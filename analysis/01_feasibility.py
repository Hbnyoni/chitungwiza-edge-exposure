"""Feasibility check for the Chitungwiza urban growth and particulate exposure study (28 October 2026).

Sites across Greater Harare: GHSL built-up growth 1990 to 2025, WorldPop 2000 to 2020, GHAP PM2.5 (2017 to 2022),
MAIAC AOD monthly climatology 2015 to 2025 (dry season Aug to Oct against wet season Dec to Feb), and a 1 km
cell sample relating dry-season AOD to recent built-up growth. OSM road-surface tag completeness is checked in 02.
Usage: python analysis/01_feasibility.py --project YOUR_EARTH_ENGINE_PROJECT
"""
from pathlib import Path
import argparse, json
import ee
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)

# approximate suburb centres and radii (km); planned/paved reference areas against fast-growing or informal ones
SITES = {
    'Chitungwiza': (31.075, -18.005, 6, 'high-density satellite town'),
    'Epworth': (31.150, -17.890, 3, 'informal'),
    'Caledonia': (31.205, -17.815, 2.5, 'informal, post-2005'),
    'Hopley': (30.985, -17.930, 2.5, 'informal, post-2005'),
    'Harare CBD': (31.050, -17.830, 2.5, 'planned, paved'),
    'Borrowdale': (31.095, -17.760, 3, 'planned low density, paved'),
}
BOX = ee.Geometry.Rectangle([30.85, -18.15, 31.35, -17.65])

built = {y: ee.Image(f'JRC/GHSL/P2023A/GHS_BUILT_S/{y}').select('built_surface') for y in (1990, 2000, 2010, 2020, 2025)}
pop = {y: ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('year', y)).filter(ee.Filter.eq('country', 'ZWE')).first()
       for y in (2000, 2010, 2020)}
pm = ee.ImageCollection('projects/sat-io/open-datasets/GHAP/GHAP_Y1K_PM25').mean().rename('pm')
aod = ee.ImageCollection('MODIS/061/MCD19A2_GRANULES').select('Optical_Depth_055').filterDate('2015-01-01', '2026-01-01')
clim = {m: aod.filter(ee.Filter.calendarRange(m, m, 'month')).mean().multiply(0.001) for m in range(1, 13)}
dry = ee.ImageCollection([clim[m] for m in (8, 9, 10)]).mean().rename('aod_dry')
wet = ee.ImageCollection([clim[m] for m in (12, 1, 2)]).mean().rename('aod_wet')

rows = []
for name, (lon, lat, r, kind) in SITES.items():
    g = ee.Geometry.Point(lon, lat).buffer(r * 1000)
    img = ee.Image.cat([built[y].rename(f'built_{y}') for y in built] + [pop[y].rename(f'pop_{y}') for y in pop])
    s = img.reduceRegion(ee.Reducer.sum(), g, 100, maxPixels=1e9).getInfo()
    m = ee.Image.cat([pm, dry, wet]).reduceRegion(ee.Reducer.mean(), g, 1000, maxPixels=1e9).getInfo()
    row = {'site': name, 'type': kind, 'radius_km': r}
    row.update({f'built_km2_{y}': s[f'built_{y}'] / 1e6 for y in built})
    row.update({f'pop_{y}': s[f'pop_{y}'] for y in pop})
    row.update(m); rows.append(row)
    print(name, 'done')
df = pd.DataFrame(rows)
df['built_growth_2000_2025_pct'] = 100 * (df.built_km2_2025 / df.built_km2_2000 - 1)
df['pop_growth_2000_2020_pct'] = 100 * (df.pop_2020 / df.pop_2000 - 1)
df['aod_dry_wet_ratio'] = df.aod_dry / df.aod_wet
df.to_csv(OUT / 'feasibility_sites.csv', index=False)

# monthly AOD climatology per site
mon = []
for name, (lon, lat, r, kind) in SITES.items():
    g = ee.Geometry.Point(lon, lat).buffer(r * 1000)
    vals = ee.Dictionary({str(m): clim[m].reduceRegion(ee.Reducer.mean(), g, 1000).get('Optical_Depth_055') for m in clim}).getInfo()
    mon += [{'site': name, 'month': int(k), 'aod': v} for k, v in vals.items()]
pd.DataFrame(mon).to_csv(OUT / 'feasibility_aod_monthly.csv', index=False)

# 1 km cells: does dry-season AOD (and its dry-wet excess) rise with recent built-up growth, after old built-up?
new_built = built[2020].subtract(built[2000]).max(0).rename('new_built')
cells = ee.Image.cat([new_built, built[2000].rename('old_built'), pop[2020].rename('pop'), pm, dry, wet]) \
    .reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(crs='EPSG:4326', scale=1000)
smp = cells.sample(BOX, scale=1000, geometries=True).getInfo()['features']
cdf = pd.DataFrame([f['properties'] | {'lon': f['geometry']['coordinates'][0], 'lat': f['geometry']['coordinates'][1]} for f in smp]).dropna()
cdf['new_built_share'] = cdf.new_built / 1e4   # m2 built per 100 m pixel / pixel area -> share of land
cdf['old_built_share'] = cdf.old_built / 1e4
cdf['aod_excess'] = cdf.aod_dry - cdf.aod_wet
cdf.to_csv(OUT / 'feasibility_cells.csv', index=False)

X = np.column_stack([np.ones(len(cdf)), cdf.new_built_share, cdf.old_built_share])
out = {'n_cells': len(cdf)}
for y in ('aod_dry', 'aod_excess', 'pm'):
    b, *_ = np.linalg.lstsq(X, cdf[y].values, rcond=None)
    res = cdf[y].values - X @ b; s2 = res @ res / (len(cdf) - 3)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    out[y] = {'b_new_built': b[1], 't_new_built': b[1] / se[1], 'b_old_built': b[2], 't_old_built': b[2] / se[2]}
json.dump(out, open(OUT / 'feasibility_cells_ols.json', 'w'), indent=2)
pd.set_option('display.width', 250)
print(df.round(3).to_string()); print(json.dumps(out, indent=2))

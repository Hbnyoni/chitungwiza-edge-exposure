"""Ward time series for Chitungwiza and its periphery (wards within 12 km), 1990 to 2025 (28 October 2026).

Per ward and year: GHSL built-up surface (5-year epochs), Landsat dry-season NDBI (May to September median,
year +/- 1), WorldPop population (GP 2000 to 2020, R2025A 2015 to 2025), Google Open Buildings Temporal counts
(2016 to 2023), V5.GL annual PM2.5 (2000 to 2022) and GHAP daily PM2.5 days above the WHO 24-h guideline (2017 to 2022).
Usage: python analysis/04_ward_time_series.py --project YOUR_EARTH_ENGINE_PROJECT
"""
from pathlib import Path
import argparse, json, time
import ee
import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
B = ROOT / 'data' / 'boundaries'
p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)

# study wards: all Chitungwiza wards plus any ward within 12 km of the Chitungwiza district boundary
w = gpd.read_file(B / 'harare_ADM3.geojson').to_crs(32736)
d = gpd.read_file(B / 'harare_ADM2.geojson').to_crs(32736)
core = d[d.shapeName == 'Chitungwiza'].geometry.union_all()
w = w[w.intersects(core.buffer(12000))].copy()
w['district'] = w.shapeName.str.rsplit(' ', n=1).str[0]
w['zone'] = w.district.where(w.district == 'Chitungwiza', 'Periphery')
w['dist_km'] = w.geometry.centroid.distance(core) / 1000
w['area_km2'] = w.area / 1e6
w = w.to_crs(4326)
w[['shapeID', 'shapeName', 'district', 'zone', 'dist_km', 'area_km2', 'geometry']].to_file(B / 'study_wards.geojson', driver='GeoJSON')
print(len(w), 'wards:', w.district.value_counts().to_dict())
FC = ee.FeatureCollection(json.loads(w[['shapeID', 'geometry']].to_json()))
AOI = FC.geometry().bounds()

CACHE = ROOT / 'data' / 'ee_cache'; CACHE.mkdir(parents=True, exist_ok=True)

def reduce(img, scale, reducer, key):
    """reduceRegions over the wards, cached per step and retried on dropped connections."""
    f = CACHE / f'{key}.csv'
    if f.exists(): return pd.read_csv(f)
    for attempt in range(5):
        try:
            fc = img.reduceRegions(FC, reducer, scale).getInfo()['features']; break
        except Exception as err:
            print(key, 'attempt', attempt + 1, 'failed:', str(err)[:80]); time.sleep(30)
    else:
        raise SystemExit(f'{key}: Earth Engine unavailable, rerun to resume')
    df = pd.DataFrame([x['properties'] for x in fc]); df.to_csv(f, index=False); return df

def landsat_ndbi(year):
    def prep(img, nir, swir):
        qa = img.select('QA_PIXEL'); clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        sr = img.select([nir, swir]).multiply(0.0000275).add(-0.2)
        return sr.normalizedDifference([swir, nir]).rename('ndbi').updateMask(clear)
    win = lambda c: c.filterBounds(AOI).filterDate(f'{year - 1}-01-01', f'{year + 2}-01-01').filter(ee.Filter.calendarRange(5, 9, 'month'))
    if year <= 2010:
        col = win(ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')).map(lambda i: prep(i, 'SR_B4', 'SR_B5'))
    else:
        col = win(ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))) \
            .map(lambda i: prep(i, 'SR_B5', 'SR_B6'))
    return col.median()

rows = []
def add(year, var, df, col):
    for _, r in df.iterrows(): rows.append({'shapeID': r.shapeID, 'year': year, 'var': var, 'value': r[col]})

for y in range(1990, 2030, 5):
    add(y, 'built_km2', reduce(ee.Image(f'JRC/GHSL/P2023A/GHS_BUILT_S/{y}').select('built_surface').divide(1e6), 100, ee.Reducer.sum(), f'built_{y}'), 'sum')
    add(y, 'ndbi', reduce(landsat_ndbi(y), 30, ee.Reducer.mean(), f'ndbi_{y}'), 'mean')
    print('built/ndbi', y)
for y in range(2000, 2021, 5):
    img = ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('year', y)).filter(ee.Filter.eq('country', 'ZWE')).first()
    add(y, 'pop_gp', reduce(img, 100, ee.Reducer.sum(), f'popgp_{y}'), 'sum')
R25 = ee.ImageCollection('WorldPop/GP/100m/R2025A/v1/pop').filterBounds(AOI)
for y in range(2015, 2026, 5):
    add(y, 'pop_r2025a', reduce(R25.filter(ee.Filter.calendarRange(y, y, 'year')).mosaic(), 100, ee.Reducer.sum(), f'popr25_{y}'), 'sum')
print('population')
OB = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1').filterBounds(AOI)
for y in range(2016, 2024):
    img = OB.filter(ee.Filter.calendarRange(y, y, 'year')).mosaic().select('building_fractional_count').multiply(64)  # 0.5 m counts sampled on the 4 m grid
    add(y, 'buildings', reduce(img, 4, ee.Reducer.sum(), f'bldg_{y}'), 'sum')
print('buildings')
PM = ee.ImageCollection('projects/sat-io/open-datasets/GLOBAL-SATELLITE-PM25/ANNUAL')
for y in range(2000, 2023):
    add(y, 'pm25', reduce(PM.filter(ee.Filter.calendarRange(y, y, 'year')).first(), 1000, ee.Reducer.mean(), f'pm_{y}'), 'mean')
print('pm25 annual')
GD = ee.ImageCollection('projects/sat-io/open-datasets/GHAP/GHAP_D1K_PM25').filterBounds(AOI)
for y in range(2017, 2023):
    c = GD.filter(ee.Filter.calendarRange(y, y, 'year'))
    add(y, 'days_gt15', reduce(c.map(lambda i: i.gt(15)).sum(), 1000, ee.Reducer.mean(), f'd15_{y}'), 'mean')
    add(y, 'ghap_mean', reduce(c.mean(), 1000, ee.Reducer.mean(), f'ghap_{y}'), 'mean')
    print('ghap', y)

ts = pd.DataFrame(rows).merge(w[['shapeID', 'shapeName', 'district', 'zone', 'dist_km', 'area_km2']], on='shapeID')
ts.to_csv(OUT / 'ward_time_series.csv', index=False)
summ = ts.pivot_table(index=['var', 'year'], columns='zone', values='value', aggfunc='mean')
print(summ.round(3).to_string())

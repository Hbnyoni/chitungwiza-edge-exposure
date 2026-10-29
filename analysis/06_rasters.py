"""Raster window for the Chitungwiza maps (28 October 2026).

One 40 x 40 km window centred on Chitungwiza district in UTM 36S (EPSG:32736), every layer on an exact grid:
  built_{y}.tif      GHSL built-up surface share of each 100 m cell, 1990 to 2025 in 5-year epochs
  ndbi_{y}.tif       Landsat dry-season (May to September) median NDBI, 30 m, 1990 to 2025 in 5-year steps
  pop_{y}.tif        WorldPop people per 100 m cell (GP 2000, 2010, 2020; R2025A 2025)
  bldg_{y}.tif       Google Open Buildings Temporal building count per 100 m cell, 2016 and 2023
  pm25_{y}.tif       V5.GL annual PM2.5, 1 km, 2000 to 2022 (ug m-3)
  d15.tif            GHAP mean days a year above the WHO 24-h guideline (15 ug m-3), 2017 to 2022, 1 km
Usage: python analysis/06_rasters.py --project YOUR_EARTH_ENGINE_PROJECT
"""
from pathlib import Path
import argparse, json, time
from concurrent.futures import ThreadPoolExecutor
import ee
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'rasters'; OUT.mkdir(parents=True, exist_ok=True)
p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)
EPSG, HALF = 32736, 20000
d = gpd.read_file(ROOT / 'data/boundaries/harare_ADM2.geojson').to_crs(EPSG)
c = d[d.shapeName == 'Chitungwiza'].geometry.union_all().centroid
X, Y = round(c.x / 1000) * 1000, round(c.y / 1000) * 1000
json.dump({'epsg': EPSG, 'x': X, 'y': Y, 'half_width_m': HALF}, open(OUT / 'window.json', 'w'), indent=1)
AOI = ee.Geometry.Rectangle([30.85, -18.20, 31.30, -17.80])

def ndbi(year):
    def prep(img, nir, swir):
        qa = img.select('QA_PIXEL'); clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        return img.select([nir, swir]).multiply(0.0000275).add(-0.2).normalizedDifference([swir, nir]).updateMask(clear)
    win = lambda col: col.filterBounds(AOI).filterDate(f'{year - 1}-01-01', f'{year + 2}-01-01').filter(ee.Filter.calendarRange(5, 9, 'month'))
    if year <= 2010:
        return win(ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')).map(lambda i: prep(i, 'SR_B4', 'SR_B5')).median()
    l89 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
    return win(l89).map(lambda i: prep(i, 'SR_B5', 'SR_B6')).median()

pop_gp = lambda y: ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('year', y)).filter(ee.Filter.eq('country', 'ZWE')).first()
R25 = ee.ImageCollection('WorldPop/GP/100m/R2025A/v1/pop').filterBounds(AOI)
OB = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1').filterBounds(AOI)
PM = ee.ImageCollection('projects/sat-io/open-datasets/GLOBAL-SATELLITE-PM25/ANNUAL')
GD = ee.ImageCollection('projects/sat-io/open-datasets/GHAP/GHAP_D1K_PM25').filterBounds(AOI).filterDate('2017-01-01', '2023-01-01')
proj100 = ee.Projection(f'EPSG:{EPSG}').atScale(100)

layers = {}
for y in range(1990, 2030, 5):
    layers[f'built_{y}'] = (ee.Image(f'JRC/GHSL/P2023A/GHS_BUILT_S/{y}').select('built_surface').divide(1e4), 100)
    layers[f'ndbi_{y}'] = (ndbi(y), 30)
for y in (2000, 2010, 2020):
    layers[f'pop_{y}'] = (pop_gp(y), 100)
layers['pop_2025'] = (R25.filter(ee.Filter.calendarRange(2025, 2025, 'year')).mosaic(), 100)
for y in (2016, 2023):
    b = OB.filter(ee.Filter.calendarRange(y, y, 'year')).mosaic().select('building_fractional_count').multiply(64)  # 0.5 m counts sampled on the 4 m grid
    layers[f'bldg_{y}'] = (b.setDefaultProjection(ee.Projection(f'EPSG:{EPSG}').atScale(4)).reduceResolution(ee.Reducer.mean(), maxPixels=1024).multiply(625)
                           .reproject(proj100), 100)
for y in range(2000, 2023):
    layers[f'pm25_{y}'] = (PM.filter(ee.Filter.calendarRange(y, y, 'year')).first(), 1000)
layers['d15'] = (GD.map(lambda i: i.gt(15)).sum().divide(6), 1000)

def fetch(item):
    name, (img, scale) = item
    f = OUT / f'{name}.tif'
    if f.exists(): return name
    n = 2 * HALF // scale
    for attempt in range(5):
        try:
            data = ee.data.computePixels({
                'expression': img.rename('v').toFloat().unmask(-9999), 'fileFormat': 'GEO_TIFF',
                'grid': {'dimensions': {'width': n, 'height': n}, 'crsCode': f'EPSG:{EPSG}',
                         'affineTransform': {'scaleX': scale, 'shearX': 0, 'translateX': X - HALF,
                                             'shearY': 0, 'scaleY': -scale, 'translateY': Y + HALF}}})
            f.write_bytes(data); print(name, flush=True); return name
        except Exception as err:
            print(name, 'attempt', attempt + 1, str(err)[:80], flush=True); time.sleep(20)
    return None

with ThreadPoolExecutor(2) as pool:  # noncommercial concurrency limit
    done = list(pool.map(fetch, layers.items()))
missing = [k for k, v in zip(layers, done) if v is None]
print('missing:', missing or 'none')

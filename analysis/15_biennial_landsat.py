"""Landsat every two years, 1990 to 2026, on the Chitungwiza frame (29 October 2026).

For each even year: the median of cloud-free dry-season (May to September) Landsat surface reflectance scenes, as a
natural-colour composite (red, green, blue) and as NDBI, at 30 m on the 20 x 14 km map frame (UTM 36S). Landsat 5 TM
is used to 2011, Landsat 7 ETM+ for 2012 (SLC-off gaps filled by the median, then by the adjacent dry seasons), and
Landsat 8 and 9 OLI from 2013. Where a pixel has no clear scene in the year, the composite of the year before and
after fills it. Draws two portrait small-multiple figures (19 panels each).
Usage: python analysis/15_biennial_landsat.py --project YOUR_EARTH_ENGINE_PROJECT
"""
import argparse, time
from concurrent.futures import ThreadPoolExecutor
import ee
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from gis_common import *

p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)
OUTD = RAS / 'biennial'; OUTD.mkdir(exist_ok=True)
YEARS = list(range(1990, 2027, 2))
AOI = ee.Geometry.Rectangle([30.85, -18.20, 31.30, -17.80])
X0, Y1 = round(EXTENT[0] / 30) * 30, round(EXTENT[3] / 30) * 30
NX, NY = int(np.ceil((EXTENT[1] - X0) / 30)), int(np.ceil((Y1 - EXTENT[2]) / 30))

def sr(col, bands):
    """Clear-sky surface reflectance renamed to blue, green, red, nir, swir1."""
    def prep(img):
        qa = img.select('QA_PIXEL')
        clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0)).And(qa.bitwiseAnd(1 << 1).eq(0))
        out = img.select(bands, ['blue', 'green', 'red', 'nir', 'swir1']).multiply(0.0000275).add(-0.2).updateMask(clear)
        return out.copyProperties(img, ['system:time_start'])  # arithmetic drops the date, which the dry-season filter needs
    return col.map(prep)

L5 = sr(ee.ImageCollection('LANDSAT/LT05/C02/T1_L2'), ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5'])
L7 = sr(ee.ImageCollection('LANDSAT/LE07/C02/T1_L2'), ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5'])
L89 = sr(ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')),
         ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6'])

def collection(y):
    return L5 if y <= 2011 else (L7 if y == 2012 else L89)

def composite(y):
    dry = lambda c, a, b: c.filterBounds(AOI).filterDate(f'{a}-05-01', f'{b}-10-01').filter(ee.Filter.calendarRange(5, 9, 'month'))
    one = dry(collection(y), y, y).median()
    three = dry(collection(y - 1).merge(collection(y)).merge(collection(y + 1)), y - 1, y + 1).median()
    return one.unmask(three)

def fetch(item):
    name, img = item
    f = OUTD / f'{name}.tif'
    if f.exists(): return name
    for attempt in range(5):
        try:
            f.write_bytes(ee.data.computePixels({
                'expression': img.toFloat().unmask(-9999), 'fileFormat': 'GEO_TIFF',
                'grid': {'dimensions': {'width': NX, 'height': NY}, 'crsCode': f'EPSG:{EPSG}',
                         'affineTransform': {'scaleX': 30, 'shearX': 0, 'translateX': X0, 'shearY': 0, 'scaleY': -30, 'translateY': Y1}}}))
            print(name, flush=True); return name
        except Exception as err:
            print(name, 'attempt', attempt + 1, str(err)[:80], flush=True); time.sleep(20)
    return None

jobs = []
for y in YEARS:
    c = composite(y)
    jobs.append((f'rgb_{y}', c.select(['red', 'green', 'blue'])))
    jobs.append((f'ndbi_{y}', c.normalizedDifference(['swir1', 'nir']).rename('ndbi')))
with ThreadPoolExecutor(2) as pool:  # noncommercial concurrency limit
    done = list(pool.map(fetch, jobs))
missing = [k for (k, _), v in zip(jobs, done) if v is None]
assert not missing, missing

def rd(name):
    with rasterio.open(OUTD / f'{name}.tif') as src:
        a = src.read().astype(float); b = src.bounds
    a[a < -9000] = np.nan
    return a, [b.left, b.right, b.bottom, b.top]

# ---- natural colour: one common stretch for every year so years are comparable ----------------------------------
rgbs = {y: rd(f'rgb_{y}') for y in YEARS}
allv = np.concatenate([a[np.isfinite(a)] for a, _ in rgbs.values()])
lo, hi = np.percentile(allv, [1, 99])
P = []
for y in YEARS:
    a, e = rgbs[y]
    img = np.clip((np.moveaxis(a, 0, -1) - lo) / (hi - lo), 0, 1) ** 0.8          # gamma lifts the dark miombo
    img = np.where(np.isfinite(img), img, 1.0)
    sensor = 'TM' if y <= 2011 else ('ETM+' if y == 2012 else 'OLI')
    P.append((f'{y}', img, e, f'Landsat {sensor}'))
all_years('biennial_landsat_rgb', P, None, None, None, ncols=4, rgb=True)

# ---- NDBI ----------------------------------------------------------------------------------------------------------
EDGE = CHIT.buffer(3000).difference(CHIT)
P = []
for y in YEARS:
    a, e = rd(f'ndbi_{y}'); a = a[0]
    mi, me = mask(CHIT, a, e), mask(EDGE, a, e)
    P.append((str(y), a, e, f'In {np.nanmean(a[mi]):+.3f} | edge {np.nanmean(a[me]):+.3f}'))
all_years('biennial_landsat_ndbi', P, 'RdYlBu_r', TwoSlopeNorm(0, -0.3, 0.3),
          'Dry-season NDBI (Landsat TM, ETM+ and OLI, 30 m)', extend='both', ncols=4)
import pandas as pd
pd.DataFrame([{'year': y, 'ndbi_inside': float(t.split()[1]), 'ndbi_edge': float(t.split()[-1])} for (y, (_, _, _, t)) in zip(YEARS, P)]) \
    .to_csv(RES / 'biennial_ndbi_inside_edge.csv', index=False)
print('done')

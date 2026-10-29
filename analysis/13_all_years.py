"""All-years multi-panel maps (one panel per year, coal-paper layout) for Chitungwiza and its edge (29 October 2026).

Downloads GHAP days above 15 ug m-3 for each year 2017 to 2022 (data/rasters/annual/d15_{y}.tif), then draws:
  allyears_builtup (GHSL 1990 to 2025), allyears_buildings (2016 to 2023), allyears_population (R2025A 2015 to 2025),
  allyears_ndbi (Landsat 8/9 2015 to 2025), allyears_pm25 (V5.GL 2000 to 2022), allyears_days_who24h (GHAP 2017 to 2022).
Usage: python analysis/13_all_years.py --project YOUR_EARTH_ENGINE_PROJECT
"""
import argparse, time
import ee
import numpy as np
import rasterio
from matplotlib.colors import LogNorm, Normalize, TwoSlopeNorm
from gis_common import *

p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)
AN = RAS / 'annual'
AOI = ee.Geometry.Rectangle([30.85, -18.20, 31.30, -17.80])
GD = ee.ImageCollection('projects/sat-io/open-datasets/GHAP/GHAP_D1K_PM25').filterBounds(AOI)
for y in range(2017, 2023):
    f = AN / f'd15_{y}.tif'
    if f.exists(): continue
    img = GD.filter(ee.Filter.calendarRange(y, y, 'year')).map(lambda i: i.gt(15)).sum()
    for attempt in range(5):
        try:
            n = 2 * H // 1000
            f.write_bytes(ee.data.computePixels({
                'expression': img.rename('v').toFloat().unmask(-9999), 'fileFormat': 'GEO_TIFF',
                'grid': {'dimensions': {'width': n, 'height': n}, 'crsCode': f'EPSG:{EPSG}',
                         'affineTransform': {'scaleX': 1000, 'shearX': 0, 'translateX': X - H, 'shearY': 0, 'scaleY': -1000, 'translateY': Y + H}}}))
            break
        except Exception as err:
            print(y, 'attempt', attempt + 1, str(err)[:80]); time.sleep(20)

def rd(path):
    with rasterio.open(path) as src:
        a = src.read(1).astype(float); b = src.bounds
    a[a < -9000] = np.nan
    return crop(a, [b.left, b.right, b.bottom, b.top])

def inside(a, e, how):
    m = mask(CHIT, a, e)
    return np.nansum(a[m]) if how == 'sum' else np.nanmean(a[m])

# built-up, every GHSL epoch
P = []
for y in range(1990, 2030, 5):
    a, e = rd(RAS / f'built_{y}.tif')
    P.append((str(y), np.where(a > 0.01, a * 100, np.nan), e, f'Inside {inside(a, e, "sum") * 0.01:.1f} km²'))
all_years('allyears_builtup', P, 'YlOrBr', Normalize(0, 60), 'Built-up surface, % of 100 m cell (GHSL)', extend='max', background='#f7f7f7')
# buildings per km2
P = []
for y in range(2016, 2024):
    a, e = rd(AN / f'bldg_{y}.tif')
    P.append((str(y), np.where(a * 100 > 50, a * 100, np.nan), e, f'Inside {inside(a, e, "sum"):,.0f}'))
all_years('allyears_buildings', P, 'viridis_r', LogNorm(50, 10000), 'Buildings per km² (Open Buildings Temporal)', extend='both', background='#f7f7f7')
# population per km2
P = []
for y in range(2015, 2026):
    a, e = rd(AN / f'pop_{y}.tif'); a = np.nan_to_num(a)
    P.append((str(y), np.where(a * 100 > 10, a * 100, np.nan), e, f'Inside {inside(a, e, "sum") / 1e3:,.0f}k'))
all_years('allyears_population', P, 'magma_r', LogNorm(10, 50000), 'People per km² (WorldPop R2025A, 100 m)', extend='both')
# NDBI
P = []
for y in range(2015, 2026):
    a, e = rd(AN / f'ndbi_{y}.tif')
    P.append((str(y), a, e, f'Inside {inside(a, e, "mean"):+.3f}'))
all_years('allyears_ndbi', P, 'RdYlBu_r', TwoSlopeNorm(0, -0.3, 0.3), 'Dry-season NDBI (Landsat 8/9)', extend='both')
# annual PM2.5
P = []
for y in range(2000, 2023):
    a, e = rd(RAS / f'pm25_{y}.tif')
    P.append((str(y), a, e, f'{inside(a, e, "mean"):.1f} µg/m³'))
all_years('allyears_pm25', P, 'YlOrRd', Normalize(10, 22), 'Annual PM$_{2.5}$ (µg m$^{-3}$, V5.GL); WHO guideline 5', extend='both')
# days above the WHO 24-h guideline
P = []
for y in range(2017, 2023):
    a, e = rd(AN / f'd15_{y}.tif')
    P.append((str(y), a, e, f'Inside {inside(a, e, "mean"):.0f} days'))
all_years('allyears_days_who24h', P, 'OrRd', Normalize(100, 365), 'Days with PM$_{2.5}$ > 15 µg m$^{-3}$ (GHAP); WHO allows 3 to 4', extend='both')
print('done')

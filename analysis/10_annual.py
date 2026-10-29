"""Annual change at the edge of Chitungwiza, 2015 to 2025 (29 October 2026).

Downloads annual layers on the 06_rasters.py grid (data/rasters/annual/):
  bldg_{2016..2023}   Open Buildings Temporal building count per 100 m cell
  ndbi_{2015..2025}   Landsat 8/9 May to September median NDBI of that year, 30 m
  pop_{2015..2025}    WorldPop R2025A people per 100 m cell
then draws the year-built map (first year a cell gains buildings), NDBI every two years, and annual charts inside
Chitungwiza against the 3 km edge outside it.
Usage: python analysis/10_annual.py --project YOUR_EARTH_ENGINE_PROJECT
"""
from pathlib import Path
import argparse, json, time
from concurrent.futures import ThreadPoolExecutor
import ee
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm
from gis_common import *

p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)
AN = RAS / 'annual'; AN.mkdir(exist_ok=True)
AOI = ee.Geometry.Rectangle([30.85, -18.20, 31.30, -17.80])
proj100 = ee.Projection(f'EPSG:{EPSG}').atScale(100)
OB = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1').filterBounds(AOI)
R25 = ee.ImageCollection('WorldPop/GP/100m/R2025A/v1/pop').filterBounds(AOI)
L89 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')).filterBounds(AOI)

def ndbi(year):
    def prep(img):
        qa = img.select('QA_PIXEL'); clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        return img.select(['SR_B5', 'SR_B6']).multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B6', 'SR_B5']).updateMask(clear)
    return L89.filterDate(f'{year}-05-01', f'{year}-10-01').map(prep).median()

layers = {}
for y in range(2016, 2024):
    b = OB.filter(ee.Filter.calendarRange(y, y, 'year')).mosaic().select('building_fractional_count').multiply(64)  # 0.5 m counts on the 4 m grid
    layers[f'bldg_{y}'] = (b.setDefaultProjection(ee.Projection(f'EPSG:{EPSG}').atScale(4))
                           .reduceResolution(ee.Reducer.mean(), maxPixels=1024).multiply(625).reproject(proj100), 100)
for y in range(2015, 2026):
    layers[f'ndbi_{y}'] = (ndbi(y), 30)
    layers[f'pop_{y}'] = (R25.filter(ee.Filter.calendarRange(y, y, 'year')).mosaic(), 100)

def fetch(item):
    name, (img, scale) = item
    f = AN / f'{name}.tif'
    if f.exists(): return name
    n = 2 * H // scale
    for attempt in range(5):
        try:
            data = ee.data.computePixels({
                'expression': img.rename('v').toFloat().unmask(-9999), 'fileFormat': 'GEO_TIFF',
                'grid': {'dimensions': {'width': n, 'height': n}, 'crsCode': f'EPSG:{EPSG}',
                         'affineTransform': {'scaleX': scale, 'shearX': 0, 'translateX': X - H,
                                             'shearY': 0, 'scaleY': -scale, 'translateY': Y + H}}})
            f.write_bytes(data); return name
        except Exception as err:
            print(name, 'attempt', attempt + 1, str(err)[:80], flush=True); time.sleep(20)
    return None

with ThreadPoolExecutor(2) as pool:  # noncommercial concurrency limit
    done = list(pool.map(fetch, layers.items()))
missing = [k for k, v in zip(layers, done) if v is None]
assert not missing, missing

def rd(name):
    import rasterio
    with rasterio.open(AN / f'{name}.tif') as src:
        a = src.read(1).astype(float); b = src.bounds
    a[a < -9000] = np.nan
    return crop(a, [b.left, b.right, b.bottom, b.top])

EDGE = CHIT.buffer(3000).difference(CHIT)
def zone_masks(a, e): return mask(CHIT, a, e), mask(EDGE, a, e)

# ---- annual table: inside against the 3 km edge -------------------------------------------------------------
rows = []
for y in range(2015, 2026):
    a, e = rd(f'pop_{y}'); mi, me = zone_masks(a, e); a = np.nan_to_num(a)
    rows.append({'year': y, 'var': 'population', 'inside': a[mi].sum(), 'edge': a[me].sum()})
    a, e = rd(f'ndbi_{y}'); mi, me = zone_masks(a, e)
    rows.append({'year': y, 'var': 'ndbi', 'inside': np.nanmean(a[mi]), 'edge': np.nanmean(a[me])})
for y in range(2016, 2024):
    a, e = rd(f'bldg_{y}'); mi, me = zone_masks(a, e); a = np.nan_to_num(a)
    rows.append({'year': y, 'var': 'buildings', 'inside': a[mi].sum(), 'edge': a[me].sum()})
ann = pd.DataFrame(rows); ann.to_csv(RES / 'annual_inside_edge.csv', index=False)
print(ann.pivot_table(index='year', columns='var', values=['inside', 'edge']).round(3).to_string())

# ---- year-built map ---------------------------------------------------------------------------------------
b = np.stack([np.nan_to_num(rd(f'bldg_{y}')[0]) for y in range(2016, 2024)])
_, e = rd('bldg_2016')
gain = b - b[0]
first = np.full(b.shape[1:], np.nan)
for k, y in enumerate(range(2017, 2024), start=1):   # first year the cell has gained 5 or more buildings since 2016
    first[np.isnan(first) & (gain[k] >= 5)] = y
cols = plt.get_cmap('plasma_r')(np.linspace(0.08, 0.95, 7))
cmap = ListedColormap(cols); norm = BoundaryNorm(np.arange(2016.5, 2024.5), 7)
fig = plt.figure(figsize=(7.1, 7.1 * ASPECT * 0.78 + 0.9))
FH = 7.1 * ASPECT * 0.78 + 0.9
ax = fig.add_axes([0.0, 0.75 / FH, 0.78, 7.1 * 0.78 * ASPECT / FH])
ax.set_facecolor('#f7f7f7')
ax.imshow(np.where(b[0] >= 5, 1, np.nan), extent=e, origin='upper', cmap=ListedColormap(['#bdbdbd']), interpolation='nearest', zorder=1)
ax.imshow(first, extent=e, origin='upper', cmap=cmap, norm=norm, interpolation='nearest', zorder=2)
frame(ax, label_chit=True, ward_numbers=True)
scale_bar(ax, EXTENT[0] + 700, EXTENT[2] + 900, 5000, '5 km', height=250); north_arrow(ax, 0.05, 0.86, size=0.05)
inside_new = {y: gain[k][mask(CHIT, gain[k], e)].sum() for k, y in enumerate(range(2016, 2024))}
edge_new = {y: gain[k][mask(EDGE, gain[k], e)].sum() for k, y in enumerate(range(2016, 2024))}
lax = fig.add_axes([0.80, 0.75 / FH + 0.05, 0.18, 0.75])
lax.axis('off')
from matplotlib.patches import Patch
hand = [Patch(facecolor='#bdbdbd', label='Built by 2016')] + [Patch(facecolor=cols[i], label=str(2017 + i)) for i in range(7)]
lax.legend(handles=hand, loc='upper left', fontsize=6.5, frameon=False, title='First year with\n≥ 5 new buildings\nper 100 m cell', title_fontsize=6.5)
lax.text(0.0, 0.32, f'New buildings 2016 to 2023\nInside: {inside_new[2023]:,.0f}\nEdge (3 km): {edge_new[2023]:,.0f}',
         transform=lax.transAxes, fontsize=6.5, va='top')
fig.legend(handles=boundary_handles(), loc='lower left', bbox_to_anchor=(0.005, 0.05 / FH), fontsize=6.2, frameon=False, ncol=3)
fig.text(0.005, 0.4 / FH, f'Map {ZW:.0f} × {ZH:.0f} km, UTM 36S. Google Open Buildings Temporal (annual, 2016 to 2023).', fontsize=6)
save_both(fig, 'map_year_built')

# ---- NDBI every two years ---------------------------------------------------------------------------------
panels = []
for y in range(2015, 2026, 2):
    a, ee_ = rd(f'ndbi_{y}'); mi, me = zone_masks(a, ee_)
    panels.append((str(y), a, ee_, f'Inside {np.nanmean(a[mi]):+.3f} | edge {np.nanmean(a[me]):+.3f}'))
# time_panels crops again; pass the already-cropped arrays with their extents (crop is idempotent on the map extent)
time_panels('map_ndbi_biennial', panels, 'RdYlBu_r', TwoSlopeNorm(0, -0.3, 0.3),
            'NDBI, dry season (May to September median of each year, Landsat 8/9, 30 m)', ncols=3, extend='both')

# ---- annual charts ----------------------------------------------------------------------------------------
rc = pd.read_csv(RES / 'roads_over_time_class.csv')
fig, axs = plt.subplots(2, 2, figsize=(7.1, 5.4))
plt.subplots_adjust(left=0.09, right=0.98, top=0.93, bottom=0.09, hspace=0.45, wspace=0.3)
C = {'inside': FOCUS, 'edge': '#2166ac'}; LAB = {'inside': 'Inside Chitungwiza', 'edge': 'Edge (3 km outside)'}
def chart(ax, var, scale, ylabel, title, letter):
    d = ann[ann['var'] == var].set_index('year')
    for z in ('inside', 'edge'):
        ax.plot(d.index, d[z] / scale, '-o', color=C[z], ms=3, lw=1.4, label=LAB[z])
    ax.set_title(title, fontsize=8, fontweight='bold', loc='left'); ax.set_ylabel(ylabel, fontsize=7)
    ax.text(-0.15, 1.06, letter, transform=ax.transAxes, fontsize=10, fontweight='bold')
    ax.tick_params(labelsize=6.5); ax.grid(axis='y', color='0.9', lw=0.5); ax.set_axisbelow(True)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.set_xticks(range(2015, 2026, 2)); ax.set_xlim(2014.5, 2025.5)
chart(axs[0, 0], 'buildings', 1e3, 'Buildings (thousands)', 'Buildings (Open Buildings Temporal)', '(a)')
chart(axs[0, 1], 'population', 1e3, 'People (thousands)', 'Population (WorldPop R2025A)', '(b)')
chart(axs[1, 0], 'ndbi', 1, 'Mean NDBI', 'Dry-season NDBI (Landsat 8/9)', '(c)')
ax = axs[1, 1]
for zn, col, lab in (('Chitungwiza', FOCUS, 'Inside Chitungwiza'), ('Periphery', '#2166ac', '12 km periphery')):
    d = rc[rc.zone == zn].set_index('year')
    ax.plot(d.index, d.get('track', 0), '-o', color=col, ms=3, lw=1.4, label=f'{lab}: tracks')
    ax.plot(d.index, d.drop(columns=['zone']).sum(axis=1), '--', color=col, lw=1, label=f'{lab}: all roads')
ax.set_title('Mapped roads (OpenStreetMap history)', fontsize=8, fontweight='bold', loc='left'); ax.set_ylabel('Road length (km)', fontsize=7)
ax.text(-0.15, 1.06, '(d)', transform=ax.transAxes, fontsize=10, fontweight='bold'); ax.tick_params(labelsize=6.5)
ax.grid(axis='y', color='0.9', lw=0.5); ax.set_xticks(range(2015, 2026, 2)); ax.set_xlim(2014.5, 2025.5)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
ax.legend(fontsize=5.6, frameon=False, loc='upper left')
axs[0, 0].legend(fontsize=6, frameon=False, loc='upper left')
save_both(fig, 'plot_annual_edge')

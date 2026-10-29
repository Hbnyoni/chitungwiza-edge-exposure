"""Shared cartography for the Chitungwiza maps (28 October 2026).

Maps are framed on Chitungwiza district plus a 3 km buffer (about 20 x 14 km, UTM 36S), cut from the 40 x 40 km
raster window of 06_rasters.py. geoBoundaries districts (ADM2) and wards (ADM3, Chitungwiza wards numbered), OSM
roads, raster reading and masks, north arrow, scale bar and the common time-series panel layout (one panel per year,
identical extent, shared colour bar).
"""
from pathlib import Path
import json
import numpy as np
import geopandas as gpd
import rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as MPolygon, Rectangle
from shapely.geometry import box, LineString

ROOT = Path(__file__).resolve().parents[1]
RES, FIG, RAS, BND = ROOT / 'results', ROOT / 'figures', ROOT / 'data/rasters', ROOT / 'data/boundaries'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.6})
NAVY = '#1f2d3d'; FOCUS = '#b2182b'
W = json.load(open(RAS / 'window.json')); EPSG = W['epsg']
X, Y, H = W['x'], W['y'], W['half_width_m']
WIN = box(X - H, Y - H, X + H, Y + H)
dist_all = gpd.read_file(BND / 'harare_ADM2.geojson').to_crs(EPSG).clip(WIN)
chit = dist_all[dist_all.shapeName == 'Chitungwiza']
BUF = 3000
_b = chit.total_bounds
EXTENT = [_b[0] - BUF, _b[2] + BUF, _b[1] - BUF, _b[3] + BUF]       # xmin, xmax, ymin, ymax
ZOOM = box(EXTENT[0], EXTENT[2], EXTENT[1], EXTENT[3])
ZW, ZH = (EXTENT[1] - EXTENT[0]) / 1000, (EXTENT[3] - EXTENT[2]) / 1000
ASPECT = ZH / ZW
dist = dist_all.clip(ZOOM.buffer(2000))
wards = gpd.read_file(BND / 'harare_ADM3.geojson').to_crs(EPSG).clip(ZOOM.buffer(2000))
cwards = wards[wards.shapeName.str.startswith('Chitungwiza')].copy()
cwards['num'] = cwards.shapeName.str.split().str[-1]
CHIT = chit.geometry.union_all()
study = gpd.read_file(BND / 'study_wards.geojson').to_crs(EPSG)

ROAD_CLASS = {'motorway': 'Primary', 'trunk': 'Primary', 'primary': 'Primary', 'secondary': 'Secondary and tertiary',
              'tertiary': 'Secondary and tertiary', 'unclassified': 'Residential and minor', 'residential': 'Residential and minor',
              'living_street': 'Residential and minor', 'service': 'Residential and minor', 'track': 'Track (unformed)'}
ROAD_STYLE = {'Primary': ('#252525', 1.1), 'Secondary and tertiary': ('#525252', 0.8),
              'Residential and minor': ('#969696', 0.35), 'Track (unformed)': ('#a6611a', 0.45)}
PAVED = {'paved', 'asphalt', 'concrete', 'paving_stones', 'sett', 'concrete:plates', 'chipseal', 'metal'}
UNPAVED = {'unpaved', 'gravel', 'dirt', 'ground', 'earth', 'sand', 'compacted', 'fine_gravel', 'mud', 'grass', 'pebblestone'}

def roads(year):
    """OSM roads on 1 January of `year` (Overpass snapshot) as a GeoDataFrame in the map CRS."""
    f = ROOT / 'data/ohsome' / f'roads_{year}.json'
    els = json.load(open(f, encoding='utf-8'))['elements']
    rec = []
    for e in els:
        if len(e.get('geometry', [])) < 2: continue
        t = e.get('tags', {}); s = t.get('surface')
        rec.append({'cls': ROAD_CLASS.get(t.get('highway'), 'Residential and minor'),
                    'surface': 'Paved' if s in PAVED else 'Unpaved' if s in UNPAVED else 'Not recorded',
                    'geometry': LineString([(g['lon'], g['lat']) for g in e['geometry']])})
    g = gpd.GeoDataFrame(rec, crs=4326).to_crs(EPSG)
    g = g.clip(ZOOM); g['km'] = g.length / 1000
    return g

def save(fig, path, **kw):
    """Save a figure, deleting any old file first (OneDrive can refuse an in-place overwrite)."""
    Path(path).unlink(missing_ok=True)
    fig.savefig(path, **kw)

def save_both(fig, name):
    save(fig, FIG / f'{name}.png', dpi=600); save(fig, FIG / f'{name}.pdf', dpi=300); plt.close(fig)

def north_arrow(ax, x, y, size=0.06):
    t = ax.transAxes
    ax.add_patch(MPolygon([[x, y + size], [x - size * 0.4, y - size * 0.6], [x, y - size * 0.3]], closed=True, transform=t,
                          facecolor=NAVY, edgecolor=NAVY, lw=0.6, zorder=20))
    ax.add_patch(MPolygon([[x, y + size], [x + size * 0.4, y - size * 0.6], [x, y - size * 0.3]], closed=True, transform=t,
                          facecolor='white', edgecolor=NAVY, lw=0.6, zorder=20))
    ax.text(x, y + size * 1.15, 'N', transform=t, ha='center', va='bottom', fontsize=8, fontweight='bold', color=NAVY, zorder=20)

def scale_bar(ax, x0, y0, length_m, label, height=None, segments=4):
    height = height or length_m * 0.04
    step = length_m / segments
    for k in range(segments):
        ax.add_patch(Rectangle((x0 + k * step, y0), step, height, facecolor=NAVY if k % 2 == 0 else 'white',
                               edgecolor=NAVY, lw=0.5, zorder=20))
    for v, s in ((0, '0'), (length_m, label)):
        ax.text(x0 + v, y0 - height * 0.8, s, ha='center', va='top', fontsize=6.5, color=NAVY, zorder=20,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.3))

def read(name):
    with rasterio.open(RAS / f'{name}.tif') as src:
        a = src.read(1).astype(float); b = src.bounds
    a[a < -9000] = np.nan
    return a, [b.left, b.right, b.bottom, b.top]

def crop(a, ext):
    """Cut a window raster to the map extent; returns (array, extent)."""
    res = (ext[1] - ext[0]) / a.shape[1]
    c0 = int((EXTENT[0] - ext[0]) // res); c1 = int(np.ceil((EXTENT[1] - ext[0]) / res))
    r0 = int((ext[3] - EXTENT[3]) // res); r1 = int(np.ceil((ext[3] - EXTENT[2]) / res))
    return a[r0:r1, c0:c1], [ext[0] + c0 * res, ext[0] + c1 * res, ext[3] - r1 * res, ext[3] - r0 * res]

def mask(geom, arr, ext):
    """Boolean mask of cells whose centre lies inside geom (same shape as arr)."""
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin
    res = (ext[1] - ext[0]) / arr.shape[1]
    return ~geometry_mask([geom], arr.shape, from_origin(ext[0], ext[3], res, res))

def aggregate(a, k):
    """Sum a 100 m array into k x k blocks (NaN treated as 0)."""
    a = np.nan_to_num(a); n = a.shape[0] // k * k
    return a[:n, :n].reshape(n // k, k, n // k, k).sum(axis=(1, 3))

def frame(ax, wards_on=True, label_chit=True, ward_numbers=False):
    """Boundaries on top of a raster: wards light, districts dark, Chitungwiza in red; optional ward numbers."""
    if wards_on: wards.boundary.plot(ax=ax, color='0.35', lw=0.3, zorder=4)
    dist.boundary.plot(ax=ax, color='0.1', lw=0.7, zorder=5)
    chit.boundary.plot(ax=ax, color='white', lw=2.2, zorder=6)
    chit.boundary.plot(ax=ax, color=FOCUS, lw=1.1, zorder=7)
    ax.set_xlim(EXTENT[:2]); ax.set_ylim(EXTENT[2:]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    if ward_numbers:
        for _, r in cwards.iterrows():
            p = r.geometry.representative_point()
            ax.text(p.x, p.y, r.num, fontsize=5, ha='center', va='center', color='k', zorder=11,
                    bbox=dict(boxstyle='circle,pad=0.12', facecolor='white', edgecolor='0.3', lw=0.3, alpha=0.85))
    if label_chit:
        ax.text(0.98, 0.97, 'Chitungwiza', transform=ax.transAxes, fontsize=6.5, color=FOCUS, fontweight='bold', zorder=12,
                ha='right', va='top', bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=0.6))

def panel_letter(ax, s):
    ax.text(0.02, 0.98, s, transform=ax.transAxes, fontsize=10, fontweight='bold', va='top', zorder=30,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=0.8))

def boundary_handles():
    return [Line2D([], [], color=FOCUS, lw=1.0, label='Chitungwiza district'),
            Line2D([], [], color='0.1', lw=0.6, label='District boundary'),
            Line2D([], [], color='0.35', lw=0.4, label='Ward boundary (Chitungwiza wards numbered)')]

def time_panels(name, panels, cmap, norm, cbar_label, ncols=3, extend='neither', cbar_ticks=None, cbar_ticklabels=None,
                background='#f0f0f0', extra=None, ward_numbers_first=True):
    """One map per year on the same extent; panels = list of (title, array, extent, box_text)."""
    n = len(panels); nrows = int(np.ceil(n / ncols))
    foot, head = 1.0, 0.22                                    # inches reserved below and above the panels
    pw = (7.1 * 0.98 - 0.03 * (ncols - 1)) / ncols
    figh = nrows * pw * ASPECT * 1.1 + foot + head
    fig, axs = plt.subplots(nrows, ncols, figsize=(7.1, figh), squeeze=False)
    plt.subplots_adjust(left=0.01, right=0.99, top=1 - head / figh, bottom=foot / figh, wspace=0.03, hspace=0.12)
    for k, (ax, (title, arr, ext, txt)) in enumerate(zip(axs.flat, panels)):
        ax.set_facecolor(background)
        arr, ext = crop(arr, ext)
        im = ax.imshow(arr, extent=ext, origin='upper', cmap=cmap, norm=norm, interpolation='nearest', zorder=1)
        frame(ax, label_chit=(k == 0), ward_numbers=(k == 0 and ward_numbers_first))
        ax.set_title(title, fontsize=8, pad=2, fontweight='bold')
        panel_letter(ax, '(' + 'abcdefghijkl'[k] + ')')
        if txt: ax.text(0.02, 0.03, txt, transform=ax.transAxes, fontsize=6, va='bottom', zorder=10,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.88, pad=1.0))
        if extra: extra(ax, k)
    for ax in axs.flat[n:]: ax.axis('off')
    cax = fig.add_axes([0.30, 0.6 / figh, 0.40, 0.11 / figh])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal', extend=extend)
    if cbar_ticks is not None:
        cb.set_ticks(cbar_ticks)
        if cbar_ticklabels is not None: cb.set_ticklabels(cbar_ticklabels); cb.ax.tick_params(length=0)
    cb.set_label(cbar_label, fontsize=7); cb.ax.tick_params(labelsize=6.5)
    fig.legend(handles=boundary_handles(), loc='lower left', bbox_to_anchor=(0.01, 0.05 / figh), fontsize=6.3, frameon=False)
    sb = fig.add_axes([0.78, 0.08 / figh, 0.2, 0.75 / figh]); sb.axis('off'); sb.set_xlim(0, 10000); sb.set_ylim(0, 4000)
    scale_bar(sb, 500, 2100, 5000, '5 km', height=350)
    north_arrow(sb, 0.85, 0.55, size=0.3)
    sb.text(0.0, -0.08, f'All panels {ZW:.0f} × {ZH:.0f} km, UTM 36S', transform=sb.transAxes, fontsize=6)
    save_both(fig, name)

def all_years(name, panels, cmap, norm, cbar_label, extend='neither', background='#f0f0f0', cbar_ticks=None, ncols=None, rgb=False):
    """Coal-paper small multiples: one panel per year on the same Chitungwiza frame, in reading order, with a footer
    strip holding the legend, colour bar, scale bar and north arrow. panels = list of (title, array, extent, box_text)."""
    n = len(panels); ncols = ncols or (4 if n <= 12 else 5)
    nrows = int(np.ceil(n / ncols))
    pw = 7.1 * 0.98 / ncols
    foot = 0.8
    figh = nrows * pw * ASPECT * 1.16 + foot + 0.12
    fig, axs = plt.subplots(nrows, ncols, figsize=(7.1, figh), squeeze=False)
    plt.subplots_adjust(left=0.01, right=0.99, top=1 - 0.12 / figh, bottom=foot / figh, wspace=0.03, hspace=0.16)
    for k, (ax, (title, arr, ext, txt)) in enumerate(zip(axs.flat, panels)):
        ax.set_facecolor(background)
        if rgb: im = ax.imshow(arr, extent=ext, origin='upper', interpolation='nearest', zorder=1)
        else:
            arr, ext = crop(arr, ext)
            im = ax.imshow(arr, extent=ext, origin='upper', cmap=cmap, norm=norm, interpolation='nearest', zorder=1)
        wards.boundary.plot(ax=ax, color='0.35', lw=0.15, zorder=4)
        dist.boundary.plot(ax=ax, color='0.1', lw=0.45, zorder=5)
        chit.boundary.plot(ax=ax, color='white', lw=1.4, zorder=6); chit.boundary.plot(ax=ax, color=FOCUS, lw=0.7, zorder=7)
        ax.set_xlim(EXTENT[:2]); ax.set_ylim(EXTENT[2:]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, fontsize=7.5, pad=1.5, fontweight='bold')
        if txt: ax.text(0.02, 0.03, txt, transform=ax.transAxes, fontsize=5.4, va='bottom', zorder=10,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=0.6))
    for ax in axs.flat[n:]: ax.axis('off')
    fig.legend(handles=[Line2D([], [], color=FOCUS, lw=1.0, label='Chitungwiza district'),
                        Line2D([], [], color='0.1', lw=0.6, label='District boundary'),
                        Line2D([], [], color='0.35', lw=0.4, label='Ward boundary')],
               loc='lower left', bbox_to_anchor=(0.01, 0.06 / figh), fontsize=6, frameon=False)
    if not rgb:
        cax = fig.add_axes([0.33, 0.45 / figh, 0.36, 0.1 / figh])
        cb = fig.colorbar(im, cax=cax, orientation='horizontal', extend=extend)
        if cbar_ticks is not None: cb.set_ticks(cbar_ticks)
        cb.set_label(cbar_label, fontsize=6.3); cb.ax.tick_params(labelsize=6)
    else:
        fig.text(0.5, 0.4 / figh, 'Natural colour (red, green, blue), dry-season median, one common stretch for all years',
                 ha='center', fontsize=6.3)
    sb = fig.add_axes([0.76, 0.06 / figh, 0.23, 0.68 / figh]); sb.axis('off'); sb.set_xlim(0, 10000); sb.set_ylim(0, 4000)
    scale_bar(sb, 300, 2000, 5000, '5 km', height=350)
    north_arrow(sb, 0.85, 0.55, size=0.3)
    sb.text(0.0, -0.05, f'All panels {ZW:.0f} × {ZH:.0f} km, UTM 36S', transform=sb.transAxes, fontsize=5.8)
    save_both(fig, name)

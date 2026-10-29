"""Maps for the Chitungwiza paper (29 October 2026), framed on Chitungwiza district and its edge (3 km buffer):
study area, built-up growth, NDBI, population, change by ward, roads over time, PM2.5 against the WHO guidelines
and the mapped attributable-mortality risk.
Usage: python analysis/08_maps.py   (after 04 to 07 and 05b)
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize, TwoSlopeNorm, BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from gis_common import *

cdr = json.load(open(ROOT / 'data/worldbank_cdr_zwe.json', encoding='utf-8'))[1]
CDR = {int(x['date']): x['value'] / 1000 for x in cdr if x['value'] is not None}
BETA = np.log(1.08) / 10
ts = pd.read_csv(RES / 'ward_time_series.csv')
hw = pd.read_csv(RES / 'ward_health.csv')
OUTSIDE = ZOOM.difference(CHIT)

def pop100(year):
    """People per km2 on the 100 m grid, cropped to the map extent."""
    a, ext = read(f'pop_{year}')
    return crop(np.nan_to_num(a) * 100, ext)

def inside_outside(arr, ext, per_cell):
    """Sum of arr * per_cell inside Chitungwiza and in the rest of the map extent."""
    m = mask(CHIT, arr, ext); a = np.nan_to_num(arr) * per_cell
    return a[m].sum(), a[~m].sum()

def single(ax, arr, ext, cmap, norm, label, letter, title, extend='neither', ward_numbers=False, bg='#f0f0f0'):
    ax.set_facecolor(bg)
    im = ax.imshow(arr, extent=ext, origin='upper', cmap=cmap, norm=norm, interpolation='nearest', zorder=1)
    frame(ax, label_chit=False, ward_numbers=ward_numbers)
    panel_letter(ax, letter); ax.set_title(title, fontsize=8, pad=2, fontweight='bold')
    cax = ax.inset_axes([0.15, -0.09, 0.7, 0.035])
    cb = plt.colorbar(im, cax=cax, orientation='horizontal', extend=extend)
    cb.set_label(label, fontsize=6.5); cb.ax.tick_params(labelsize=6)
    return im

def ward_choropleth(ax, values, cmap, norm, label, letter, title, extend='both', fmt='{:.0f}'):
    w = wards.merge(values.rename('v'), left_on='shapeName', right_index=True, how='left')
    ax.set_facecolor('#f0f0f0')
    w.plot(ax=ax, column='v', cmap=cmap, norm=norm, edgecolor='none', zorder=1, missing_kwds={'color': '#e0e0e0'})
    frame(ax, label_chit=False)
    for _, r in w[w.shapeName.str.startswith('Chitungwiza')].iterrows():
        if np.isfinite(r.v):
            p = r.geometry.representative_point()
            ax.text(p.x, p.y, fmt.format(r.v), fontsize=4.8, ha='center', va='center', zorder=11,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.2))
    panel_letter(ax, letter); ax.set_title(title, fontsize=8, pad=2, fontweight='bold')
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = ax.inset_axes([0.15, -0.09, 0.7, 0.035])
    cb = plt.colorbar(sm, cax=cax, orientation='horizontal', extend=extend)
    cb.set_label(label, fontsize=6.5); cb.ax.tick_params(labelsize=6)

def footer(fig, y=0.005):
    fig.legend(handles=boundary_handles(), loc='lower left', bbox_to_anchor=(0.01, y), fontsize=6.2, frameon=False, ncol=3)
    sb = fig.add_axes([0.80, y, 0.18, 0.045]); sb.axis('off'); sb.set_xlim(0, 10000); sb.set_ylim(0, 4000)
    scale_bar(sb, 500, 2300, 5000, '5 km', height=450); north_arrow(sb, 0.88, 0.5, size=0.35)

# ---- Fig 1 study area -----------------------------------------------------------------------------------
def fig_study_area():
    r = roads(2025)
    zwe = gpd.read_file(ROOT / 'data/boundaries/ZWE_ADM1.geojson')
    FW, MW = 7.1, 5.0                                   # figure width and main-map width (inches)
    FH = MW * ASPECT + 0.45
    fig = plt.figure(figsize=(FW, FH))
    ax = fig.add_axes([0.0, 0.4 / FH, MW / FW, MW * ASPECT / FH])
    d, ext = pop100(2025)
    im = ax.imshow(np.where(d > 10, d, np.nan), extent=ext, origin='upper', cmap='magma_r', norm=LogNorm(10, 50000),
                   interpolation='nearest', zorder=1, alpha=0.85)
    ax.set_facecolor('#f0f0f0')
    for surf, col, lw in (('Not recorded', '#9e9e9e', 0.25), ('Unpaved', '#a6611a', 0.6), ('Paved', '#08306b', 0.9)):
        r[r.surface == surf].plot(ax=ax, color=col, lw=lw, zorder=3)
    frame(ax, label_chit=False, ward_numbers=True)
    for name, g in dist.groupby('shapeName'):
        if name == 'Chitungwiza': continue
        p = g.geometry.intersection(ZOOM).union_all()
        if p.is_empty or p.area < 4e6: continue
        p = p.representative_point()
        ax.text(p.x, p.y, name, fontsize=7, color='0.15', ha='center', zorder=12, style='italic',
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.65, pad=0.4))
    ax.text(0.98, 0.97, 'Chitungwiza', transform=ax.transAxes, fontsize=8, color=FOCUS, fontweight='bold', ha='right', va='top',
            zorder=12, bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=0.6))
    scale_bar(ax, EXTENT[0] + 700, EXTENT[2] + 900, 5000, '5 km', height=250)
    north_arrow(ax, 0.05, 0.86, size=0.05)
    # locators: Zimbabwe, then Greater Harare districts
    lax = fig.add_axes([0.72, 0.73, 0.27, 0.24])
    zwe.plot(ax=lax, facecolor='#f7f7f7', edgecolor='0.5', lw=0.3)
    gpd.GeoSeries([WIN], crs=EPSG).to_crs(4326).boundary.plot(ax=lax, color=FOCUS, lw=0.9)
    lax.set_xticks([]); lax.set_yticks([]); lax.set_title('Zimbabwe', fontsize=6.5, pad=1.5)
    hax = fig.add_axes([0.72, 0.44, 0.27, 0.24])
    dist_all.plot(ax=hax, facecolor='#f7f7f7', edgecolor='0.4', lw=0.3)
    chit.plot(ax=hax, facecolor=FOCUS, edgecolor='none', alpha=0.8)
    gpd.GeoSeries([ZOOM]).boundary.plot(ax=hax, color='k', lw=0.7)
    for name, g in dist_all.groupby('shapeName'):
        if name in ('Harare', 'Epworth', 'Seke', 'Ruwa', 'Goromonzi'):
            p = g.geometry.union_all().representative_point(); hax.text(p.x, p.y, name, fontsize=4.8, ha='center', color='0.25')
    hax.set_xlim(X - H, X + H); hax.set_ylim(Y - H, Y + H); hax.set_aspect('equal'); hax.set_xticks([]); hax.set_yticks([])
    hax.set_title('Greater Harare (40 × 40 km)', fontsize=6.5, pad=1.5)
    for a in (lax, hax):
        for s in a.spines.values(): s.set_color('0.6')
    cax = fig.add_axes([0.735, 0.385, 0.245, 0.02])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal'); cb.set_label('People per km$^2$, 2025 (100 m)', fontsize=6.3)
    cb.ax.tick_params(labelsize=5.8)
    inside = r.clip(CHIT).groupby('surface').km.sum()
    hand = [Line2D([], [], color='#08306b', lw=1.3, label=f"Paved ({inside.get('Paved', 0):,.0f} km inside)"),
            Line2D([], [], color='#a6611a', lw=1.3, label=f"Unpaved ({inside.get('Unpaved', 0):,.0f} km)"),
            Line2D([], [], color='#9e9e9e', lw=1.3, label=f"Surface not recorded ({inside.get('Not recorded', 0):,.0f} km)")] \
           + boundary_handles()
    fig.legend(handles=hand[:3] + [Line2D([], [], color=FOCUS, lw=1.0, label='Chitungwiza district'),
                                   Line2D([], [], color='0.1', lw=0.6, label='District boundary'),
                                   Line2D([], [], color='0.35', lw=0.4, label='Ward boundary')],
               loc='upper left', bbox_to_anchor=(0.715, 0.30), fontsize=5.8, frameon=False,
               title='OSM roads, 1 January 2025', title_fontsize=6)
    fig.text(0.005, 0.12 / FH, f'Map {ZW:.0f} × {ZH:.0f} km, UTM 36S. Numbers are Chitungwiza wards 1 to 25. Boundaries: geoBoundaries '
             '(ZIMSTAT/OCHA). Population: WorldPop R2025A.', fontsize=6)
    save_both(fig, 'map_study_area')

# ---- Fig 2 built-up growth (GHSL) -------------------------------------------------------------------------
def fig_built():
    panels = []
    for y in (1990, 2000, 2010, 2015, 2020, 2025):
        a, ext = read(f'built_{y}'); a, ext = crop(a, ext)
        i, o = inside_outside(a, ext, 0.01)
        panels.append((str(y), np.where(a > 0.01, a * 100, np.nan), ext, f'Inside {i:.1f} km$^2$ | edge {o:.1f} km$^2$'))
    time_panels('map_builtup', panels, 'YlOrBr', Normalize(0, 60), 'Built-up surface, % of each 100 m cell (GHSL)',
                ncols=3, extend='max', background='#f7f7f7')

# ---- Fig 3 NDBI -----------------------------------------------------------------------------------------
def fig_ndbi():
    panels = []
    for y in (1990, 2000, 2005, 2015, 2020, 2025):
        a, ext = read(f'ndbi_{y}'); a, ext = crop(a, ext)
        m = mask(CHIT, a, ext)
        panels.append((str(y), a, ext, f'Inside {np.nanmean(a[m]):+.3f} | edge {np.nanmean(a[~m]):+.3f}'))
    time_panels('map_ndbi', panels, 'RdYlBu_r', TwoSlopeNorm(0, -0.3, 0.3), 'NDBI, dry season (May to September median, Landsat 30 m)',
                ncols=3, extend='both')

# ---- Fig 4 population ------------------------------------------------------------------------------------
def fig_population():
    panels = []
    for y in (2000, 2010, 2020, 2025):
        d, ext = pop100(y)
        i, o = inside_outside(d, ext, 0.01)
        src = 'R2025A' if y == 2025 else 'GP'
        panels.append((f'{y} (WorldPop {src})', np.where(d > 10, d, np.nan), ext, f'Inside {i / 1e3:,.0f}k | edge {o / 1e3:,.0f}k people'))
    time_panels('map_population', panels, 'magma_r', LogNorm(10, 50000), 'People per km$^2$ (100 m cells)', ncols=2, extend='both')

# ---- Fig 5 change inside and at the edge, by cell and by ward ----------------------------------------------
def fig_change():
    fig, axs = plt.subplots(2, 2, figsize=(7.1, 6.3))
    plt.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16, wspace=0.04, hspace=0.36)
    b0, ext = read('built_1990'); b1, _ = read('built_2025')
    db, e = crop((np.nan_to_num(b1) - np.nan_to_num(b0)) * 100, ext)
    single(axs[0, 0], np.where(np.abs(db) > 0.5, db, np.nan), e, 'RdBu_r', TwoSlopeNorm(0, -20, 40),
           'Change in built-up surface, percentage points', '(a)', 'Built-up change, 1990 to 2025', extend='both', bg='white')
    o0, ext = read('bldg_2016'); o1, _ = read('bldg_2023')
    nb, e = crop(np.clip(np.nan_to_num(o1) - np.nan_to_num(o0), 0, None) * 100, ext)
    single(axs[0, 1], np.where(nb > 50, nb, np.nan), e, 'viridis_r', LogNorm(50, 5000),
           'New buildings per km$^2$ (Open Buildings Temporal)', '(b)', 'New buildings, 2016 to 2023', extend='both', bg='white')
    p = ts[ts['var'] == 'pop_gp'].pivot_table(index='shapeName', columns='year', values='value')
    single_w = 100 * (p[2020] / p[2000] - 1)
    ward_choropleth(axs[1, 0], single_w, 'PuOr_r', TwoSlopeNorm(0, -20, 100), 'Population change by ward (%)', '(c)',
                    'Population change by ward, 2000 to 2020', fmt='{:+.0f}')
    bl = ts[ts['var'] == 'buildings'].pivot_table(index='shapeName', columns='year', values='value')
    ar = ts.drop_duplicates('shapeName').set_index('shapeName').area_km2
    gain = (bl[2023] - bl[2016]) / ar
    ward_choropleth(axs[1, 1], gain, 'YlGnBu', Normalize(0, 400), 'New buildings per km$^2$ of ward', '(d)',
                    'New buildings by ward, 2016 to 2023', extend='max')
    footer(fig)
    save_both(fig, 'map_change')

# ---- Fig 6 roads over time --------------------------------------------------------------------------------
def fig_roads():
    fig, axs = plt.subplots(2, 2, figsize=(7.1, 5.6))
    plt.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.13, wspace=0.03, hspace=0.12)
    for k, (ax, y) in enumerate(zip(axs.flat, (2010, 2015, 2020, 2025))):
        r = roads(y); ax.set_facecolor('white')
        for cls, (col, lw) in ROAD_STYLE.items():
            g = r[r.cls == cls]
            if len(g): g.plot(ax=ax, color=col, lw=lw, zorder=3 if cls != 'Track (unformed)' else 2)
        frame(ax, label_chit=(k == 0), ward_numbers=False)
        ax.set_title(f'1 January {y}', fontsize=8, pad=2, fontweight='bold'); panel_letter(ax, f'({"abcd"[k]})')
        ri = r.clip(CHIT)
        ax.text(0.02, 0.03, f'Inside: {ri.km.sum():,.0f} km ({ri[ri.cls == "Track (unformed)"].km.sum():,.0f} km tracks)\n'
                f'Map: {r.km.sum():,.0f} km ({r[r.cls == "Track (unformed)"].km.sum():,.0f} km tracks)',
                transform=ax.transAxes, fontsize=6, va='bottom', zorder=10, bbox=dict(facecolor='white', edgecolor='none', alpha=0.88, pad=1.2))
    hand = [Line2D([], [], color=c, lw=max(lw, 0.8) * 1.3, label=k) for k, (c, lw) in ROAD_STYLE.items()]
    fig.legend(handles=hand, loc='lower left', ncol=4, fontsize=6.3, frameon=False, bbox_to_anchor=(0.01, 0.065))
    footer(fig)
    fig.text(0.01, 0.003, 'OpenStreetMap history (Overpass snapshots); growth in mapped length combines new roads and new mapping.', fontsize=5.8)
    save_both(fig, 'map_roads_over_time')

# ---- Fig 7 PM2.5 and the WHO guidelines -------------------------------------------------------------------
def fig_pm():
    panels = []
    for y in (2000, 2005, 2010, 2015, 2020, 2022):
        a, ext = read(f'pm25_{y}'); a, ext = crop(a, ext)
        m = mask(CHIT, a, ext)
        panels.append((str(y), a, ext, f'Inside {np.nanmean(a[m]):.1f} µg m$^{{-3}}$ ({np.nanmean(a[m]) / 5:.1f}× WHO)'))
    time_panels('map_pm25', panels, 'YlOrRd', Normalize(10, 22), 'Annual PM$_{2.5}$ (µg m$^{-3}$, V5.GL, 1 km); WHO guideline 5',
                ncols=3, extend='both')
    fig, axs = plt.subplots(1, 2, figsize=(7.1, 3.3))
    plt.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.27, wspace=0.04)
    a, ext = read('d15'); a, ext = crop(a, ext)
    single(axs[0], a, ext, 'OrRd', Normalize(150, 330), 'Days a year with PM$_{2.5}$ > 15 µg m$^{-3}$ (GHAP, 1 km)', '(a)',
           'Days above the WHO 24-h guideline, 2017 to 2022', extend='both', ward_numbers=True)
    pmw = hw[hw.year.between(2018, 2022)].groupby('shapeName').pm25.mean()
    ward_choropleth(axs[1], pmw, 'YlOrRd', Normalize(14, 18), 'Annual PM$_{2.5}$ (µg m$^{-3}$), ward mean 2018 to 2022', '(b)',
                    'Ward annual PM$_{2.5}$ (WHO guideline 5)', fmt='{:.1f}')
    footer(fig)
    save_both(fig, 'map_pm25_who')

# ---- Fig 8 mapped risk: PM2.5-attributable deaths per km2 ---------------------------------------------------
def fig_risk():
    p, ext = read('pop_2020'); p = np.nan_to_num(p)
    pm = np.nanmean([read(f'pm25_{y}')[0] for y in range(2018, 2023)], axis=0)
    pm100 = np.kron(pm, np.ones((10, 10)))[:p.shape[0], :p.shape[1]]
    deaths = p * CDR[2020] * (1 - np.exp(-BETA * np.clip(pm100 - 5, 0, None)))   # per 100 m cell per year
    dk, e = crop(deaths * 100, ext)                                                 # per km2 per year
    pd_, _ = crop(p * 100, ext)
    populated = pd_ > 10
    q = np.nanpercentile(dk[populated], [20, 40, 60, 80])
    bounds = np.r_[0, q, dk[populated].max() + 1e-9]
    cls = np.where(populated, np.digitize(dk, bounds[1:-1]), np.nan)
    np.savetxt(RES / 'risk_class_breaks.csv', bounds, delimiter=',', header='deaths_per_km2_breaks', comments='')
    cmap = ListedColormap(plt.get_cmap('RdPu')(np.linspace(0.18, 0.95, 5)))
    labs = ['Very low', 'Low', 'Moderate', 'High', 'Very high']
    fig, axs = plt.subplots(1, 2, figsize=(7.1, 3.6))
    plt.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.33, wspace=0.04)
    single(axs[0], np.where(populated, dk, np.nan), e, 'RdPu', LogNorm(0.05, 30),
           'PM$_{2.5}$-attributable deaths km$^{-2}$ yr$^{-1}$ (above WHO 5 µg m$^{-3}$)', '(a)',
           'Attributable deaths per km$^2$ a year', extend='both', ward_numbers=True, bg='#d9d9d9')
    ax = axs[1]; ax.set_facecolor('#d9d9d9')
    ax.imshow(cls, extent=e, origin='upper', cmap=cmap, norm=BoundaryNorm(np.arange(-0.5, 5.5), 5), interpolation='nearest', zorder=1)
    frame(ax, label_chit=False); panel_letter(ax, '(b)'); ax.set_title('Risk class (quintiles of populated cells)', fontsize=8, pad=2, fontweight='bold')
    hand = [Patch(facecolor=cmap(i), label=f'{labs[i]} ({bounds[i]:.2f} to {bounds[i + 1]:.2f})') for i in range(5)] + \
           [Patch(facecolor='#d9d9d9', label='Unpopulated (< 10 people km$^{-2}$)')]
    ax.legend(handles=hand, loc='upper center', bbox_to_anchor=(0.5, -0.03), ncol=2, fontsize=5.8, frameon=False)
    footer(fig)
    save_both(fig, 'map_risk')
    m = mask(CHIT, dk, e)
    out = {'deaths_chitungwiza': float(dk[m].sum() * 0.01), 'deaths_edge_in_map': float(dk[~m].sum() * 0.01),
           'share_chit_cells_high_or_very_high': float(100 * np.mean(cls[m & populated] >= 3)),
           'share_edge_cells_high_or_very_high': float(100 * np.mean(cls[~m & populated] >= 3)),
           'pop_chit_2020': float(pd_[m].sum() * 0.01)}
    json.dump(out, open(RES / 'risk_map_summary.json', 'w'), indent=2); print(out)

for f in (fig_study_area, fig_built, fig_ndbi, fig_population, fig_change, fig_roads, fig_pm, fig_risk):
    f(); print(f.__name__, 'done', flush=True)

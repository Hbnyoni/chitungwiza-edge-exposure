"""Time-series charts for the Chitungwiza paper (28 October 2026): growth, NDBI, roads, PM2.5 and attributable deaths,
Chitungwiza district against its 12 km periphery.
Usage: python analysis/09_charts.py
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from gis_common import RES, save_both, FOCUS

BLUE = '#2166ac'; COL = {'Chitungwiza': FOCUS, 'Periphery': BLUE}
ts = pd.read_csv(RES / 'ward_time_series.csv')
z = pd.read_csv(RES / 'zone_health_by_year.csv')
rc = pd.read_csv(RES / 'roads_over_time_class.csv')

def zone_series(var, how):
    d = ts[ts['var'] == var]
    if how == 'sum': return d.groupby(['zone', 'year']).value.sum().unstack(0)
    return d.assign(w=d.value * d.area_km2).groupby(['zone', 'year']).apply(
        lambda g: g.w.sum() / g.area_km2[g.value.notna()].sum(), include_groups=False).unstack(0)

def style(ax, letter, title, ylabel):
    ax.set_title(title, fontsize=8, fontweight='bold', loc='left', pad=3)
    ax.text(-0.16, 1.06, letter, transform=ax.transAxes, fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=7); ax.tick_params(labelsize=6.5)
    ax.grid(axis='y', color='0.9', lw=0.5); ax.set_axisbelow(True)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)

def end_label(ax, x, y, text, color, dy=0, ha='left'):
    """Label a line at its last point instead of a legend box."""
    ax.text(x, y + dy, text, color=color, fontsize=6.3, fontweight='bold', ha=ha, va='center')

fig, axs = plt.subplots(3, 2, figsize=(7.1, 8.4))
plt.subplots_adjust(left=0.08, right=0.95, top=0.955, bottom=0.06, hspace=0.52, wspace=0.34)

# (a) built-up area
ax = axs[0, 0]; b = zone_series('built_km2', 'sum')
for zn in COL:
    ax.plot(b.index, b[zn], '-o', color=COL[zn], ms=3, lw=1.5)
    ax.fill_between(b.index, 0, b[zn], color=COL[zn], alpha=0.07, lw=0)
    end_label(ax, 2025.8, b[zn].iloc[-1], f'{zn}\n×{b[zn].iloc[-1] / b[zn].iloc[0]:.1f} since 1990', COL[zn])
ax.set_xlim(1988, 2033); ax.set_ylim(0, None); ax.set_xticks(range(1990, 2030, 5))
style(ax, '(a)', 'Built-up area (GHSL), 1990 to 2025', 'Built-up area (km$^2$)')

# (b) population: the two WorldPop releases are drawn separately and never joined
ax = axs[0, 1]; gp = zone_series('pop_gp', 'sum') / 1e3; r25 = zone_series('pop_r2025a', 'sum') / 1e3
for zn in COL:
    ax.plot(gp.index, gp[zn], '-o', color=COL[zn], ms=3, lw=1.5)
    ax.plot(r25.index, r25[zn], '--^', color=COL[zn], ms=3, lw=1, alpha=0.85)
    end_label(ax, 2025.8, r25[zn].iloc[-1], zn, COL[zn])
ax.text(0.02, 0.97, 'Solid: WorldPop GP (2000 to 2020)\nDashed: WorldPop R2025A (2015 to 2025)', transform=ax.transAxes,
        fontsize=5.8, va='top', color='0.3')
ax.set_xlim(1998, 2033); ax.set_xticks(range(2000, 2030, 5))
style(ax, '(b)', 'Population', 'People (thousands)')

# (c) NDBI
ax = axs[1, 0]; nd = zone_series('ndbi', 'mean')
ax.axvspan(2008.5, 2011.5, color='0.93', zorder=0)
ax.text(2010, 0.163, 'wetter\n2010 scene', fontsize=5.5, ha='center', va='top', color='0.45')
for zn in COL:
    ax.plot(nd.index, nd[zn], '-o', color=COL[zn], ms=3, lw=1.5)
    end_label(ax, 2025.8, nd[zn].iloc[-1], zn, COL[zn], dy=0.004 if zn == 'Periphery' else -0.004)
ax.set_xlim(1988, 2033); ax.set_xticks(range(1990, 2030, 5))
style(ax, '(c)', 'Dry-season NDBI (Landsat)', 'Mean NDBI (built and bare surface)')

# (d) mapped roads by class (periphery stacked, Chitungwiza line)
ax = axs[1, 1]
groups = {'Primary to tertiary': ['motorway', 'trunk', 'primary', 'secondary', 'tertiary'],
          'Residential and minor': ['unclassified', 'residential', 'living_street', 'service'], 'Tracks (unformed)': ['track']}
cols = {'Primary to tertiary': '#525252', 'Residential and minor': '#bdbdbd', 'Tracks (unformed)': '#a6611a'}
d = rc[rc.zone == 'Periphery'].set_index('year')
stack = [d[[c for c in g if c in d]].sum(axis=1) for g in groups.values()]
ax.stackplot(d.index, stack, colors=list(cols.values()), alpha=0.92, lw=0)
cum = np.cumsum([s.iloc[-1] for s in stack])
for (k, c), top, s in zip(cols.items(), cum, stack):
    ax.text(2025.4, top - s.iloc[-1] / 2, k, fontsize=5.8, va='center', color='0.15' if c != '#525252' else '0.25')
dc = rc[rc.zone == 'Chitungwiza'].set_index('year'); tot = dc.drop(columns='zone').sum(axis=1)
ax.plot(tot.index, tot, color=FOCUS, lw=1.8)
end_label(ax, 2025.4, tot.iloc[-1] - 120, 'Chitungwiza (all roads)', FOCUS)
ax.text(0.02, 0.97, '12 km periphery, stacked by class', transform=ax.transAxes, fontsize=5.8, va='top', color='0.3')
ax.set_xlim(2008, 2033); ax.set_xticks(range(2008, 2026, 4))
style(ax, '(d)', 'Mapped road network (OpenStreetMap history)', 'Road length (km)')

# (e) PM2.5 against WHO levels, with the interim-target bands shaded
ax = axs[2, 0]
for lo_, hi_, col in ((0, 5, '#e5f5e0'), (5, 10, '#fff7bc'), (10, 15, '#fee6ce'), (15, 25, '#fcbba1')):
    ax.axhspan(lo_, hi_, color=col, zorder=0)
for y_, lab in ((0.4, 'WHO guideline (5)'), (5.4, 'Interim target 4 (10)'), (10.4, 'Interim target 3 (15)')):
    ax.text(2000, y_, lab, fontsize=5.6, color='0.35', va='bottom')
for zn in COL:
    d = z[z.zone == zn].set_index('year')
    ax.plot(d.index, d.pm25_popw, '-o', color=COL[zn], ms=2.5, lw=1.4)
    end_label(ax, 2022.6, d.pm25_popw.iloc[-1], zn, COL[zn], dy=0.7 if zn == 'Periphery' else -0.7)
ax.set_ylim(0, 22); ax.set_xlim(1999.5, 2028); ax.set_xticks(range(2000, 2023, 4))
style(ax, '(e)', 'Population-weighted annual PM$_{2.5}$', 'PM$_{2.5}$ (µg m$^{-3}$)')

# (f) attributable deaths
ax = axs[2, 1]
for zn in COL:
    d = z[z.zone == zn].set_index('year')
    ax.fill_between(d.index, d.deaths_low, d.deaths_high, color=COL[zn], alpha=0.18, lw=0)
    ax.plot(d.index, d.deaths, '-o', color=COL[zn], ms=2.5, lw=1.4)
    end_label(ax, 2022.6, d.deaths.iloc[-1], zn, COL[zn])
ax.text(0.98, 0.97, 'Bands: RR 1.06 to 1.09 per 10 µg m$^{-3}$', transform=ax.transAxes, fontsize=5.8, color='0.35', ha='right', va='top')
ax.set_xlim(1999.5, 2028); ax.set_xticks(range(2000, 2023, 4)); ax.set_ylim(0, None)
style(ax, '(f)', 'PM$_{2.5}$-attributable deaths (above 5 µg m$^{-3}$)', 'Deaths a year')
save_both(fig, 'plot_time_series')

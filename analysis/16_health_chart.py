"""Health-impact figure for the Chitungwiza paper (29 October 2026).

(a) Days a month above the WHO 24-h guideline by calendar month, bars coloured by monthly mean PM2.5 (GHAP 2017-2022);
(b) population-weighted annual PM2.5 against the WHO guideline and interim-target bands (V5.GL 2000-2022);
(c) PM2.5-attributable deaths a year in Chitungwiza with the RR 1.06 to 1.09 range;
(d) the 25 Chitungwiza wards ranked by days above 15 ug m-3, bars coloured by attributable deaths per 100,000.
Usage: python analysis/16_health_chart.py
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from gis_common import RES, save_both, FOCUS

BLUE = '#2166ac'; GREY = '0.35'
V = json.load(open(RES / 'manuscript_numbers.json'))
mo = pd.read_csv(RES / 'monthly_exceedance.csv')
z = pd.read_csv(RES / 'zone_health_by_year.csv')
h = pd.read_csv(RES / 'ward_health.csv')

def tidy(ax, letter, title, ylabel, xlabel=None):
    ax.set_title(title, fontsize=8, fontweight='bold', loc='left', pad=4)
    ax.text(-0.13, 1.07, letter, transform=ax.transAxes, fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=7)
    if xlabel: ax.set_xlabel(xlabel, fontsize=7)
    ax.tick_params(labelsize=6.5, length=2.5)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.grid(axis='y', color='0.9', lw=0.5); ax.set_axisbelow(True)

fig = plt.figure(figsize=(7.1, 7.4))
gs = fig.add_gridspec(2, 2, left=0.08, right=0.985, top=0.95, bottom=0.07, hspace=0.36, wspace=0.32, width_ratios=[1, 1])

# (a) monthly exceedance
ax = fig.add_subplot(gs[0, 0])
cm = plt.get_cmap('YlOrRd'); nm = Normalize(10, 30)
ax.axvspan(4.5, 10.5, color='#f2efe6', zorder=0)
ax.text(7.5, 31.8, 'Dry season', ha='center', fontsize=6.3, color='0.4')
ax.bar(mo.month, mo.days_gt15, color=cm(nm(mo.pm25_mean)), edgecolor='0.3', lw=0.4, width=0.75, zorder=2)
days_in = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
ax.step(np.arange(0.5, 13.5), days_in + [31], where='post', color='0.5', lw=0.6, ls=(0, (2, 2)), zorder=3)
ax.text(12.45, 31.4, 'days in\nmonth', fontsize=5.5, color='0.45', ha='right', va='bottom')
for m_, d_ in zip(mo.month, mo.days_gt15):
    ax.text(m_, d_ + 0.5, f'{d_:.0f}', ha='center', fontsize=5.6, zorder=4)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(list('JFMAMJJASOND')); ax.set_xlim(0.4, 12.6); ax.set_ylim(0, 36)
tidy(ax, '(a)', 'Days above the WHO 24 h guideline, by month', 'Days a month with PM$_{2.5}$ > 15 µg m$^{-3}$')
ax.text(0.03, 0.97, 'WHO allows 3 to 4 days a year', transform=ax.transAxes, fontsize=6, va='top', color=FOCUS)
cax = ax.inset_axes([0.6, -0.15, 0.38, 0.03]); cb = fig.colorbar(ScalarMappable(nm, cm), cax=cax, orientation='horizontal')
cb.set_label('Monthly mean PM$_{2.5}$ (µg m$^{-3}$)', fontsize=5.8); cb.ax.tick_params(labelsize=5.5)

# (b) annual PM2.5 against the WHO bands
ax = fig.add_subplot(gs[0, 1])
bands = [(0, 5, '#e5f5e0', 'WHO guideline (≤ 5)'), (5, 10, '#fff7bc', 'Interim target 4 (10)'),
         (10, 15, '#fee6ce', 'Interim target 3 (15)'), (15, 25, '#fcbba1', 'Interim target 2 (25)')]
for lo_, hi_, col, lab in bands:
    ax.axhspan(lo_, hi_, color=col, zorder=0)
    ax.text(2000.0, (lo_ + 0.35) if hi_ <= 10 else (22.0 if lo_ == 15 else 10.35), lab, fontsize=5.6, va='bottom', ha='left', color='0.3')
for zn, col in (('Periphery', BLUE), ('Chitungwiza', FOCUS)):
    d = z[z.zone == zn].set_index('year')
    ax.plot(d.index, d.pm25_popw, '-o', color=col, ms=2.6, lw=1.4, zorder=3)
    ax.text(2022.5, d.pm25_popw.iloc[-1] + (-0.6 if zn == 'Chitungwiza' else 0.6), zn, color=col, fontsize=6.3, fontweight='bold', ha='left', va='center')
ax.set_ylim(0, 23); ax.set_xlim(1999.5, 2026.6); ax.set_xticks(range(2000, 2023, 4))
tidy(ax, '(b)', 'Annual PM$_{2.5}$ against the WHO 2021 levels', 'Population-weighted PM$_{2.5}$ (µg m$^{-3}$)')

# (c) attributable deaths
ax = fig.add_subplot(gs[1, 0])
d = z[z.zone == 'Chitungwiza'].set_index('year')
ax.bar(d.index, d.deaths, color='#d6604d', edgecolor='none', width=0.72, zorder=2)
ax.errorbar(d.index, d.deaths, yerr=[d.deaths - d.deaths_low, d.deaths_high - d.deaths], fmt='none', ecolor='0.25', elinewidth=0.6, capsize=1.3, zorder=3)
ax.text(0.98, 0.95, f"{V['deaths_in_total']:,.0f} deaths, 2000 to 2022\n{V['af_share_1822']:.1f}% of all deaths in 2018 to 2022\n"
        f"{V['rate100k_1822']:.0f} per 100,000 a year", transform=ax.transAxes, ha='right', va='top', fontsize=6.2,
        bbox=dict(facecolor='white', edgecolor='0.8', lw=0.5, pad=2.5))
ax.set_xticks(range(2000, 2023, 4)); ax.set_xlim(1999.3, 2022.7)
tidy(ax, '(c)', 'Deaths attributable to PM$_{2.5}$ above 5 µg m$^{-3}$', 'Deaths a year, Chitungwiza (RR 1.06 to 1.09)')

# (d) wards ranked by exceedance days
ax = fig.add_subplot(gs[1, 1])
w = h[(h.zone == 'Chitungwiza') & h.year.between(2017, 2022)].groupby('shapeName').agg(days=('days_gt15', 'mean'))
w['rate'] = h[(h.zone == 'Chitungwiza') & h.year.between(2018, 2022)].groupby('shapeName').deaths_per_100k.mean()
w = w.sort_values('days'); w['num'] = w.index.str.split().str[-1]
cm2 = plt.get_cmap('RdPu'); nm2 = Normalize(w.rate.min() - 1, w.rate.max())
ax.barh(range(len(w)), w.days, color=cm2(nm2(w.rate)), edgecolor='0.3', lw=0.3, height=0.72, zorder=2)
ax.set_yticks(range(len(w))); ax.set_yticklabels('Ward ' + w.num, fontsize=5.4)
ax.set_xlim(150, 365); ax.axvline(365, color='0.5', lw=0.6, ls=(0, (2, 2)))
tidy(ax, '(d)', 'Chitungwiza wards, 2017 to 2022', '', 'Days a year with PM$_{2.5}$ > 15 µg m$^{-3}$')
ax.grid(axis='x', color='0.9', lw=0.5); ax.grid(axis='y', visible=False)
cax = ax.inset_axes([0.56, 0.1, 0.4, 0.03]); cb = fig.colorbar(ScalarMappable(nm2, cm2), cax=cax, orientation='horizontal')
cb.set_label('Attributable deaths per 100,000 a year', fontsize=5.6); cb.ax.tick_params(labelsize=5.4)
cb.ax.xaxis.set_label_position('top')
save_both(fig, 'plot_health')
print('done')

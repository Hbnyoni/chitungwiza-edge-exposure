"""Every number quoted in the manuscript, computed from results/ and data/ (29 October 2026).

Inside = Chitungwiza district; edge = the 3 km band outside its boundary.
Writes results/manuscript_numbers.json. Usage: python analysis/11_numbers.py   (after 04 to 10)
"""
import json
import numpy as np
import pandas as pd
from gis_common import *

EDGE = CHIT.buffer(3000).difference(CHIT)
V = {}
def io(name, per_cell=1.0, how='sum'):
    a, e = read(name); a, e = crop(a, e)
    mi, me = mask(CHIT, a, e), mask(EDGE, a, e)
    if how == 'sum':
        a = np.nan_to_num(a) * per_cell; return a[mi].sum(), a[me].sum()
    return np.nanmean(a[mi]), np.nanmean(a[me])

# area
V['chit_area_km2'] = CHIT.area / 1e6; V['edge_area_km2'] = EDGE.area / 1e6
V['n_wards'] = int(len(cwards))
# built-up (GHSL share of 100 m cells -> km2)
for y in range(1990, 2030, 5):
    V[f'built_in_{y}'], V[f'built_edge_{y}'] = io(f'built_{y}', 0.01)
# population (GP for 2000 to 2020, R2025A annual from 10_annual)
for y in (2000, 2010, 2020):
    V[f'pop_in_{y}'], V[f'pop_edge_{y}'] = io(f'pop_{y}')
ann = pd.read_csv(RES / 'annual_inside_edge.csv')
g = lambda var, y, z: float(ann[(ann['var'] == var) & (ann.year == y)][z].iloc[0])
for y in range(2015, 2026):
    V[f'r25_in_{y}'], V[f'r25_edge_{y}'] = g('population', y, 'inside'), g('population', y, 'edge')
    V[f'ndbi_in_{y}'], V[f'ndbi_edge_{y}'] = g('ndbi', y, 'inside'), g('ndbi', y, 'edge')
for y in range(2016, 2024):
    V[f'bldg_in_{y}'], V[f'bldg_edge_{y}'] = g('buildings', y, 'inside'), g('buildings', y, 'edge')
b = ann[ann['var'] == 'buildings'].set_index('year')
V['bldg_edge_max_gain_year'] = int(b.edge.diff().idxmax()); V['bldg_edge_max_gain'] = float(b.edge.diff().max())
for y in (1990, 2000, 2005, 2015, 2020, 2025):
    V[f'ndbi5_in_{y}'], V[f'ndbi5_edge_{y}'] = io(f'ndbi_{y}', how='mean')
# roads inside and at the edge from the OSM snapshots
for y in (2010, 2015, 2020, 2025):
    r = roads(y)
    for zn, geom in (('in', CHIT), ('edge', EDGE)):
        c = r.clip(geom); c['km'] = c.length / 1000
        V[f'road_{zn}_{y}'] = c.km.sum(); V[f'track_{zn}_{y}'] = c[c.cls == 'Track (unformed)'].km.sum()
        for s in ('Paved', 'Unpaved', 'Not recorded'): V[f'road_{zn}_{y}_{s.split()[0].lower()}'] = c[c.surface == s].km.sum()
rc = pd.read_csv(RES / 'roads_over_time_class.csv')
per = rc[rc.zone == 'Periphery'].set_index('year')
V['per_track_2010'], V['per_track_2025'] = float(per.loc[2010, 'track']), float(per.loc[2025, 'track'])
V['per_road_2010'] = float(per.loc[2010].drop('zone').sum()); V['per_road_2025'] = float(per.loc[2025].drop('zone').sum())
# exposure and health (ward based, Chitungwiza zone = its 25 wards)
z = pd.read_csv(RES / 'zone_health_by_year.csv')
c = z[z.zone == 'Chitungwiza'].set_index('year'); p = z[z.zone == 'Periphery'].set_index('year')
V['pm_in_min'], V['pm_in_max'] = float(c.pm25_popw.min()), float(c.pm25_popw.max())
V['pm_in_min_year'], V['pm_in_max_year'] = int(c.pm25_popw.idxmin()), int(c.pm25_popw.idxmax())
V['pm_in_2000'], V['pm_in_2022'] = float(c.pm25_popw[2000]), float(c.pm25_popw[2022])
V['pm_in_1822'] = float(c.pm25_popw.loc[2018:2022].mean()); V['pm_per_1822'] = float(p.pm25_popw.loc[2018:2022].mean())
V['years_above_it3'] = int((c.pm25_popw > 15).sum()); V['n_years_pm'] = int(len(c))
V['pct_pop_above_aqg_min'] = float(c.pct_pop_above_AQG.min())
V['d15_in_mean'] = float(c.days_gt15_popw.loc[2017:2022].mean()); V['d15_per_mean'] = float(p.days_gt15_popw.loc[2017:2022].mean())
V['d15_in_max'], V['d15_in_max_year'] = float(c.days_gt15_popw.max()), int(c.days_gt15_popw.idxmax())
V['d15_in_min'], V['d15_in_min_year'] = float(c.days_gt15_popw.min()), int(c.days_gt15_popw.idxmin())
V['deaths_in_1822'] = float(c.deaths.loc[2018:2022].mean())
V['deaths_in_1822_lo'] = float(c.deaths_low.loc[2018:2022].mean()); V['deaths_in_1822_hi'] = float(c.deaths_high.loc[2018:2022].mean())
V['deaths_in_max'], V['deaths_in_max_year'] = float(c.deaths.max()), int(c.deaths.idxmax())
V['deaths_in_total'] = float(c.deaths.sum()); V['deaths_per_total'] = float(p.deaths.sum())
h = pd.read_csv(RES / 'ward_health.csv')
cw = h[(h.zone == 'Chitungwiza') & h.year.between(2018, 2022)].groupby('shapeName').agg(pm=('pm25', 'mean'), d=('deaths_per_100k', 'mean'))
V['ward_pm_min'], V['ward_pm_max'] = float(cw.pm.min()), float(cw.pm.max())
V['ward_pm_max_name'], V['ward_pm_min_name'] = cw.pm.idxmax(), cw.pm.idxmin()
cdr = {int(x['date']): x['value'] for x in json.load(open(ROOT / 'data/worldbank_cdr_zwe.json', encoding='utf-8'))[1] if x['value'] is not None}
V['cdr_2020'] = cdr[2020]; V['cdr_2000'] = cdr[2000]; V['cdr_2010'] = cdr[2010]
V.update({f'risk_{k}': v for k, v in json.load(open(RES / 'risk_map_summary.json')).items()})
br = np.loadtxt(RES / 'risk_class_breaks.csv', skiprows=1, delimiter=',')
V['risk_vh_lo'] = float(br[4])
mo = pd.read_csv(RES / 'monthly_exceedance.csv').set_index('month')
V['d15_aso'] = float(mo.loc[[8, 9, 10], 'days_gt15'].mean()); V['d15_dj'] = float(mo.loc[[12, 1], 'days_gt15'].mean())
V['pm_aso'] = float(mo.loc[[8, 9, 10], 'pm25_mean'].mean()); V['pm_dj'] = float(mo.loc[[12, 1], 'pm25_mean'].mean())
assert mo.days_gt15.idxmax() in (8, 9, 10) and mo.days_gt15.idxmin() in (12, 1)
wd = h[(h.zone == 'Chitungwiza') & h.year.between(2017, 2022)].groupby('shapeName').days_gt15.mean()
V['ward_d15_max'], V['ward_d15_min'] = float(wd.max()), float(wd.min())
V['ward_d15_max_name'], V['ward_d15_min_name'] = wd.idxmax(), wd.idxmin()
top = wd.sort_values(ascending=False).index[:5].str.split().str[-1].astype(int)
t5 = [str(x) for x in sorted(top)]; V['ward_d15_top5'] = ', '.join(t5[:-1]) + ' and ' + t5[-1]
# health burden in context: share of all deaths, rate per 100,000, ward spread
cy = h[(h.zone == 'Chitungwiza') & h.year.between(2018, 2022)].copy()
cy['all_deaths'] = cy['pop'] * cy.cdr
g = cy.groupby('year')[['deaths_central', 'all_deaths', 'pop']].sum()
V['af_share_1822'] = float(100 * g.deaths_central.sum() / g.all_deaths.sum())
V['rate100k_1822'] = float(1e5 * g.deaths_central.mean() / g['pop'].mean())
V['all_deaths_1822'] = float(g.all_deaths.mean())
wr = cy.groupby('shapeName').deaths_per_100k.mean()
V['ward_rate_min'], V['ward_rate_max'] = float(wr.min()), float(wr.max())
c00 = h[(h.zone == 'Chitungwiza') & (h.year == 2000)]
V['af_share_2001'] = float(100 * h[(h.zone == 'Chitungwiza') & (h.year == 2001)].af_central.mean())
json.dump(V, open(RES / 'manuscript_numbers.json', 'w'), indent=1, default=float)
for k, v in V.items(): print(k, round(v, 3) if isinstance(v, float) else v)

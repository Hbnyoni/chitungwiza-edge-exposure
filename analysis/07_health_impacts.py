"""PM2.5 exposure against the WHO 2021 guidelines and attributable mortality by ward, 2000 to 2022 (28 October 2026).

Annual guideline 5 ug m-3 and interim targets 35/25/15/10; 24-h guideline 15 ug m-3 (GHAP days above it, 2017 to 2022).
Attributable fraction AF = 1 - exp(-beta * max(C - 5, 0)), beta = ln(RR) / 10 with RR 1.08 (1.06 to 1.09) per 10 ug m-3
for natural-cause mortality (Chen & Hoek, 2020); deaths = population x crude death rate (World Bank) x AF.
Population: WorldPop GP 2000 to 2020 interpolated log-linearly between epochs, 2021 to 2022 carried forward with the
R2025A 2020 to 2025 growth rate.
Usage: python analysis/07_health_impacts.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'results'
RR = {'central': 1.08, 'low': 1.06, 'high': 1.09}
AQG, IT = 5.0, {'IT-1': 35, 'IT-2': 25, 'IT-3': 15, 'IT-4': 10, 'AQG': 5}

f = ROOT / 'data' / 'worldbank_cdr_zwe.json'
if not f.exists():
    r = requests.get('https://api.worldbank.org/v2/country/ZWE/indicator/SP.DYN.CDRT.IN?format=json&per_page=100', timeout=60)
    r.raise_for_status(); f.write_text(r.text, encoding='utf-8')
cdr = {int(x['date']): x['value'] / 1000 for x in json.loads(f.read_text(encoding='utf-8'))[1] if x['value'] is not None}

ts = pd.read_csv(RES / 'ward_time_series.csv')
meta = ts.drop_duplicates('shapeID')[['shapeID', 'shapeName', 'district', 'zone', 'dist_km', 'area_km2']]
wide = ts.pivot_table(index=['shapeID', 'year'], columns='var', values='value').reset_index()

rows = []
for sid, g in wide.groupby('shapeID'):
    g = g.set_index('year')
    gp = g['pop_gp'].dropna()
    r25 = g['pop_r2025a'].dropna() if 'pop_r2025a' in g else pd.Series(dtype=float)
    years = np.arange(2000, 2023)
    logp = np.interp(years, gp.index, np.log(gp.clip(lower=1).values))
    if len(r25) >= 2 and 2020 in r25.index and 2025 in r25.index:
        rate = np.log(r25[2025] / r25[2020]) / 5
        logp = np.where(years > 2020, np.log(max(gp[2020], 1)) + rate * (years - 2020), logp)
    for y, lp in zip(years, logp):
        c = g['pm25'].get(y, np.nan)
        row = {'shapeID': sid, 'year': y, 'pop': float(np.exp(lp)), 'pm25': c, 'cdr': cdr.get(y, np.nan),
               'days_gt15': g['days_gt15'].get(y, np.nan) if 'days_gt15' in g else np.nan}
        for k, rr in RR.items():
            af = 1 - np.exp(-np.log(rr) / 10 * max(c - AQG, 0)) if np.isfinite(c) else np.nan
            row[f'af_{k}'] = af; row[f'deaths_{k}'] = row['pop'] * row['cdr'] * af
        rows.append(row)
h = pd.DataFrame(rows).merge(meta, on='shapeID')
h['deaths_per_100k'] = 1e5 * h.deaths_central / h['pop']
h['deaths_per_km2'] = h.deaths_central / h.area_km2
h.to_csv(RES / 'ward_health.csv', index=False)

def zone_sum(d):
    pw = np.average(d.pm25, weights=d['pop'])
    out = {'pop': d['pop'].sum(), 'pm25_popw': pw, 'deaths': d.deaths_central.sum(), 'deaths_low': d.deaths_low.sum(),
           'deaths_high': d.deaths_high.sum(), 'days_gt15_popw': np.average(d.days_gt15, weights=d['pop']) if d.days_gt15.notna().all() else np.nan}
    for k, v in IT.items(): out[f'pct_pop_above_{k}'] = 100 * d['pop'][d.pm25 > v].sum() / d['pop'].sum()
    return pd.Series(out)
z = pd.concat([h.groupby(['zone', 'year']).apply(zone_sum, include_groups=False),
               h.assign(zone='All').groupby(['zone', 'year']).apply(zone_sum, include_groups=False)])
z.round(3).to_csv(RES / 'zone_health_by_year.csv')
pd.set_option('display.width', 250)
print(z.round(2).to_string())

"""Mapped road network over time from the OpenStreetMap full history (ohsome API), 2008 to 2025 (28 October 2026).

Road length (km) on 1 January each year by highway class and by surface class for Chitungwiza district and its
12 km periphery. OSM history records when roads were mapped, not when they were built, so it is read alongside
built-up growth and used for the paved/unpaved composition of the network rather than as a construction date.
Usage: python analysis/05_roads_over_time.py
"""
from pathlib import Path
import json, time
import requests
import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'; B = ROOT / 'data' / 'boundaries'
API = 'https://api.ohsome.org/v1/elements/length/groupBy/tag'
d = gpd.read_file(B / 'harare_ADM2.geojson').to_crs(32736)
core = d[d.shapeName == 'Chitungwiza'].geometry.union_all()
zones = gpd.GeoDataFrame({'id': ['Chitungwiza', 'Periphery']},
                         geometry=[core, core.buffer(12000).difference(core)], crs=32736).simplify(50).to_crs(4326)
zones = gpd.GeoDataFrame({'id': ['Chitungwiza', 'Periphery']}, geometry=zones.values, crs=4326)
BPOLYS = zones.to_json()
ROADS = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'living_street', 'service', 'track']
PAVED = ['paved', 'asphalt', 'concrete', 'paving_stones', 'sett', 'concrete:plates', 'chipseal']
UNPAVED = ['unpaved', 'gravel', 'dirt', 'ground', 'earth', 'sand', 'compacted', 'fine_gravel', 'mud', 'grass']
FILTER = 'type:way and highway in (' + ','.join(ROADS) + ')'

RAW = ROOT / 'data' / 'ohsome'; RAW.mkdir(parents=True, exist_ok=True)

def query(zone, key, values):
    f = RAW / f'{zone}_{key}.json'
    if f.exists(): return json.loads(f.read_text(encoding='utf-8'))
    for attempt in range(5):
        try:
            r = requests.post(API, data={'bpolys': BPOLYS, 'time': '2008-01-01/2025-01-01/P1Y', 'filter': FILTER,
                                         'groupByKey': key, 'groupByValues': ','.join(values)},
                              headers={'User-Agent': 'chitungwiza-exposure-study/1.0'}, timeout=600)
            r.raise_for_status(); f.write_text(r.text, encoding='utf-8'); return r.json()
        except requests.RequestException as err:
            print(zone, key, 'attempt', attempt + 1, 'failed:', str(err)[:80]); time.sleep(20)
    raise SystemExit('ohsome unavailable, try again later')

rows = []
for zone in ('Chitungwiza', 'Periphery'):
    one = zones[zones.id == zone]
    BPOLYS = one.to_json()
    for key, values in (('highway', ROADS), ('surface', PAVED + UNPAVED)):
        res = query(zone, key, values)
        for g in res['groupByResult']:
            for t in g['result']:
                rows.append({'zone': zone, 'key': key, 'value': g['groupByObject'], 'year': int(t['timestamp'][:4]),
                             'km': t['value'] / 1000})
        print(zone, key)
df = pd.DataFrame(rows)
df = df[df.value != 'remainder'].copy()
df['class'] = df.value.str.split('=').str[1]
s = df.key == 'surface'
df.loc[s, 'class'] = df.loc[s, 'class'].map(lambda v: 'paved' if v in PAVED else 'unpaved' if v in UNPAVED else 'untagged')
tot = df[df.key == 'highway'].groupby(['zone', 'year']).km.sum().rename('total_km')
surf = df[s].pivot_table(index=['zone', 'year'], columns='class', values='km', aggfunc='sum').join(tot)
surf['untagged'] = surf.total_km - surf.get('paved', 0) - surf.get('unpaved', 0)
df.to_csv(OUT / 'roads_over_time_long.csv', index=False)
surf.round(1).to_csv(OUT / 'roads_over_time_surface.csv')
hw = df[df.key == 'highway'].pivot_table(index=['zone', 'year'], columns='class', values='km', aggfunc='sum')
hw.round(1).to_csv(OUT / 'roads_over_time_class.csv')
print(surf.round(0).to_string()); print(hw.round(0).to_string())

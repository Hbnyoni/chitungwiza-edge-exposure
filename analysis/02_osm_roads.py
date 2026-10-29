"""OpenStreetMap road network and surface-tag completeness for Chitungwiza and comparison suburbs (28 October 2026).

Downloads highway ways from the Overpass API, measures length by road class and surface (paved, unpaved, untagged).
Usage: python analysis/02_osm_roads.py
"""
from pathlib import Path
import json, math, time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
RAW = ROOT / 'data' / 'osm'; RAW.mkdir(parents=True, exist_ok=True)
BOXES = {  # south, west, north, east
    'Chitungwiza': (-18.060, 31.020, -17.955, 31.130),
    'Epworth': (-17.915, 31.120, -17.865, 31.180),
    'Harare CBD': (-17.850, 31.030, -17.810, 31.070),
    'Borrowdale': (-17.785, 31.065, -17.735, 31.125),
}
PAVED = {'paved', 'asphalt', 'concrete', 'paving_stones', 'sett', 'concrete:plates', 'chipseal', 'metal'}
UNPAVED = {'unpaved', 'gravel', 'dirt', 'ground', 'earth', 'sand', 'compacted', 'fine_gravel', 'mud', 'grass', 'pebblestone'}
SERVERS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
           'https://maps.mail.ru/osm/tools/overpass/api/interpreter']
HEAD = {'User-Agent': 'chitungwiza-exposure-study/1.0', 'Accept': 'application/json'}
ROADS ='motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|track'

def length_km(coords):
    d = 0
    for (y1, x1), (y2, x2) in zip(coords, coords[1:]):
        dx = math.radians(x2 - x1) * math.cos(math.radians((y1 + y2) / 2)); dy = math.radians(y2 - y1)
        d += 6371 * math.hypot(dx, dy)
    return d

rows = []
for name, (s, w, n, e) in BOXES.items():
    f = RAW / f"{name.replace(' ', '_')}.json"
    if not f.exists():
        q = f'[out:json][timeout:120];way["highway"~"^({ROADS})$"]({s},{w},{n},{e});out tags geom;'
        for attempt in range(6):
            url = SERVERS[attempt % len(SERVERS)]
            try:
                r = requests.post(url, data={'data': q}, timeout=240, headers=HEAD); r.raise_for_status(); break
            except requests.RequestException as err:
                print(name, url, 'failed:', str(err)[:80]); time.sleep(30)
        else:
            raise SystemExit('Overpass unavailable, try again later')
        f.write_text(r.text, encoding='utf-8'); time.sleep(5)
    for el in json.loads(f.read_text(encoding='utf-8'))['elements']:
        t = el.get('tags', {}); surf = t.get('surface')
        cls = 'paved' if surf in PAVED else 'unpaved' if surf in UNPAVED else 'untagged'
        rows.append({'area': name, 'highway': t['highway'], 'surface_class': cls,
                     'km': length_km([(g['lat'], g['lon']) for g in el['geometry']])})
df = pd.DataFrame(rows)
tab = df.pivot_table(index='area', columns='surface_class', values='km', aggfunc='sum', fill_value=0)
tab['total_km'] = tab.sum(axis=1)
for c in ('paved', 'unpaved', 'untagged'):
    if c in tab: tab[f'{c}_pct'] = 100 * tab[c] / tab.total_km
tab.round(1).to_csv(OUT / 'osm_road_surface.csv')
print(tab.round(1).to_string())
print(df.groupby(['area', 'highway']).km.sum().round(1).unstack(0).to_string())

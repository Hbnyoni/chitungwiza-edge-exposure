"""OpenStreetMap road geometry snapshots for the map window (1 January 2010, 2015, 2020, 2025; Overpass attic queries).
Usage: python analysis/05b_road_snapshots.py   (after 06_rasters.py has written data/rasters/window.json)
"""
from pathlib import Path
import json, time
import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'ohsome'; RAW.mkdir(parents=True, exist_ok=True)
w = json.load(open(ROOT / 'data/rasters/window.json'))
t = Transformer.from_crs(w['epsg'], 4326, always_xy=True)
x0, y0 = t.transform(w['x'] - w['half_width_m'], w['y'] - w['half_width_m'])
x1, y1 = t.transform(w['x'] + w['half_width_m'], w['y'] + w['half_width_m'])
BBOX = f'{x0:.4f},{y0:.4f},{x1:.4f},{y1:.4f}'
ROADS = 'motorway,trunk,primary,secondary,tertiary,unclassified,residential,living_street,service,track'
SERVERS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter']
HEAD = {'User-Agent': 'chitungwiza-exposure-study/1.0', 'Accept': 'application/json'}
S, W, N, E = y0, x0, y1, x1
for year in (2010, 2015, 2020, 2025):
    f = RAW / f'roads_{year}.json'
    if f.exists(): continue
    q = (f'[out:json][timeout:600][date:"{year}-01-01T00:00:00Z"];'
         f'way["highway"~"^({ROADS.replace(",", "|")})$"]({S:.4f},{W:.4f},{N:.4f},{E:.4f});out tags geom;')
    for attempt in range(4):
        try:
            r = requests.post(SERVERS[attempt % 2], data={'data': q}, headers=HEAD, timeout=900)
            r.raise_for_status(); f.write_text(r.text, encoding='utf-8'); print(year, len(r.json()['elements']), 'ways'); break
        except requests.RequestException as err:
            print(year, 'attempt', attempt + 1, str(err)[:80]); time.sleep(60)
    time.sleep(10)

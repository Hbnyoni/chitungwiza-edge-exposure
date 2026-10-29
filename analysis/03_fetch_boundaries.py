"""geoBoundaries gbOpen Zimbabwe ADM1 to ADM3 (wards, ZIMSTAT/OCHA 2020) at a pinned commit, clipped to Greater Harare.
Usage: python analysis/03_fetch_boundaries.py
"""
from pathlib import Path
import hashlib, json
import requests
import geopandas as gpd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'boundaries'; DATA.mkdir(parents=True, exist_ok=True)
COMMIT = '9469f09'
BOX = box(30.85, -18.15, 31.35, -17.65)
prov = {}
for lvl in ('ADM1', 'ADM2', 'ADM3'):
    url = f'https://github.com/wmgeolab/geoBoundaries/raw/{COMMIT}/releaseData/gbOpen/ZWE/{lvl}/geoBoundaries-ZWE-{lvl}.geojson'
    f = DATA / f'ZWE_{lvl}.geojson'
    if not f.exists():
        r = requests.get(url, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
    prov[lvl] = {'url': url, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
    g = gpd.read_file(f)
    g[g.intersects(BOX)].to_file(DATA / f'harare_{lvl}.geojson', driver='GeoJSON')
    print(lvl, len(g), 'units;', int(g.intersects(BOX).sum()), 'in Greater Harare')
json.dump(prov, open(DATA / 'provenance.json', 'w'), indent=2)
w = gpd.read_file(DATA / 'harare_ADM3.geojson'); d = gpd.read_file(DATA / 'harare_ADM2.geojson')
print(d.shapeName.tolist())
print(w.shapeName.head(20).tolist())

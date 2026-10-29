"""Days above the WHO 24-h guideline (GHAP PM2.5 > 15 ug m-3) by calendar month, Chitungwiza, 2017 to 2022 (29 October 2026).
Writes results/monthly_exceedance.csv. Usage: python analysis/12_monthly_exceedance.py --project YOUR_EARTH_ENGINE_PROJECT
"""
import argparse, json
import ee
import geopandas as gpd
import pandas as pd
from gis_common import ROOT, RES, CHIT, EPSG

p = argparse.ArgumentParser(); p.add_argument('--project', required=True); args = p.parse_args()
ee.Initialize(project=args.project)
geom = ee.Geometry(json.loads(gpd.GeoSeries([CHIT], crs=EPSG).to_crs(4326).to_json())['features'][0]['geometry'])
GD = ee.ImageCollection('projects/sat-io/open-datasets/GHAP/GHAP_D1K_PM25').filterDate('2017-01-01', '2023-01-01').filterBounds(geom)
rows = []
for m in range(1, 13):
    c = GD.filter(ee.Filter.calendarRange(m, m, 'month'))
    days = c.map(lambda i: i.gt(15)).sum().divide(6)            # mean days a year in this month
    mean = c.mean()
    v = ee.Image.cat([days.rename('days'), mean.rename('pm')]).reduceRegion(ee.Reducer.mean(), geom, 1000).getInfo()
    rows.append({'month': m, 'days_gt15': v['days'], 'pm25_mean': v['pm']})
df = pd.DataFrame(rows); df.to_csv(RES / 'monthly_exceedance.csv', index=False)
print(df.round(2).to_string(index=False))

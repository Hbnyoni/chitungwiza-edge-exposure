# Growing at the edge: Chitungwiza peri-urban expansion, roads and PM2.5 exposure

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23764046.svg)](https://doi.org/10.5281/zenodo.23764046)

Code and derived data for *Growing at the edge: unplanned peri-urban expansion, unpaved roads and fine particulate matter exposure in Chitungwiza, Zimbabwe, 1990 to 2025*

The study follows Chitungwiza district (25 wards) and the 3 km band outside its boundary from 1990 to 2025 with open
data: GHSL built-up surface, Google Open Buildings Temporal building counts, Landsat dry-season NDBI, WorldPop population
and the OpenStreetMap road history. It compares PM2.5 exposure (V5.GL.04 annual, GHAP daily) with the 2021 WHO annual
and 24 hour guidelines and estimates attributable mortality by ward and on a 100 m risk surface. No survey, clinical or
individual-level data are used.

## Contents

| Folder | What it holds |
|---|---|
| `analysis/` | Python scripts, run in numerical order (see below); `gis_common.py` holds the shared cartography |
| `results/` | Derived datasets: ward time series (built-up, NDBI, population, buildings, PM2.5, exceedance days), ward and zone health impacts, annual inside and edge series, road length by class and surface, monthly exceedance, risk class breaks and every number quoted in the article (`manuscript_numbers.json`) |
| `data/` | Study wards (GeoJSON), World Bank crude death rates and geoBoundaries provenance with SHA-256 hashes |

Raster extracts (about 300 MB), OpenStreetMap downloads and the full geoBoundaries files are not stored here; the
scripts reacquire them.

## Reproducing the analysis

Requirements: Python 3.13 with `earthengine-api`, `pandas`, `numpy`, `geopandas`, `rasterio`, `pyproj`, `shapely`,
`requests` and `matplotlib`. Earth Engine steps need your own registered Cloud project, passed with `--project`; no
credentials are distributed.

1. `python analysis/03_fetch_boundaries.py`: geoBoundaries ZWE ADM1 to ADM3 at commit 9469f09
2. `python analysis/04_ward_time_series.py --project YOUR_PROJECT`: ward time series
3. `python analysis/02_osm_roads.py` and `python analysis/05_roads_over_time.py`: OpenStreetMap road surface and history
4. `python analysis/06_rasters.py --project YOUR_PROJECT`: raster window (writes the map grid used by later steps)
5. `python analysis/05b_road_snapshots.py`: road snapshots for 2010, 2015, 2020 and 2025
6. `python analysis/07_health_impacts.py`: WHO guideline comparison and attributable deaths
7. `python analysis/08_maps.py`, `python analysis/09_charts.py`: maps and charts
8. `python analysis/10_annual.py --project YOUR_PROJECT`: annual layers, year-built map, inside and edge series
9. `python analysis/12_monthly_exceedance.py --project YOUR_PROJECT`: exceedance days by month
10. `python analysis/13_all_years.py --project YOUR_PROJECT`: one-panel-per-year atlas
11. `python analysis/11_numbers.py`: every number quoted in the article
12. `python analysis/15_biennial_landsat.py --project YOUR_PROJECT`: Landsat natural colour and NDBI every two years, 1990 to 2026
13. `python analysis/16_health_chart.py`: health-impact figure

`01_feasibility.py` is the initial feasibility check and is kept for transparency.

## Where to get the data

Derived datasets produced by this study are in `results/`; each GitHub release is archived on Zenodo with a DOI (see
"Citation" below). All inputs are public and are reacquired by the scripts:

| Input | Access | Licence / citation |
|---|---|---|
| GHSL GHS-BUILT-S R2023A | Earth Engine `JRC/GHSL/P2023A/GHS_BUILT_S`, https://human-settlement.emergency.copernicus.eu | CC BY 4.0; Pesaresi et al. 2024 |
| Google Open Buildings Temporal v1 | Earth Engine `GOOGLE/Research/open-buildings-temporal/v1` | CC BY 4.0; Sirko et al. 2023 |
| Landsat 5, 8 and 9 Collection 2 Level 2 | Earth Engine `LANDSAT/LT05/C02/T1_L2`, `LANDSAT/LC08/C02/T1_L2`, `LANDSAT/LC09/C02/T1_L2` | USGS public domain |
| WorldPop population (GP and R2025A) | Earth Engine `WorldPop/GP/100m/pop`, `WorldPop/GP/100m/R2025A/v1/pop`, https://www.worldpop.org | CC BY 4.0; Tatem 2017 |
| V5.GL.04 annual PM2.5 | Earth Engine Community Catalog `projects/sat-io/open-datasets/GLOBAL-SATELLITE-PM25/ANNUAL`, https://sites.wustl.edu/acag/datasets/surface-pm2-5/ | van Donkelaar et al. 2021 |
| GHAP daily PM2.5 (1 km, 2017 to 2022) | Earth Engine Community Catalog `projects/sat-io/open-datasets/GHAP/GHAP_D1K_PM25` | Wei et al. 2023 |
| OpenStreetMap history | ohsome API (https://api.ohsome.org) and Overpass API | ODbL; Raifer et al. 2019 |
| geoBoundaries gbOpen ZWE ADM1 to ADM3, commit 9469f09 | https://github.com/wmgeolab/geoBoundaries/tree/9469f09 | Runfola et al. 2020 |
| World Bank crude death rates | https://data.worldbank.org/indicator/SP.DYN.CDRT.IN (copy in `data/`) | CC BY 4.0 |

## Licence

Code is released under the MIT licence (`LICENSE`). Derived datasets are released under CC BY 4.0 (`LICENSE-DATA`).
Road statistics derived from OpenStreetMap are also subject to the ODbL.

## Citation

Please cite the archived release and the associated article:

Nyoni, H. B., Moyo, P. L., Chinwadzimba, Z., Sibanda, R., & Tigere, D. (2026). *Growing at the edge: Chitungwiza peri-urban expansion, roads and PM2.5 exposure: code and derived data*
(Version 1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23764046

## Contact

Handsome Bongani Nyoni (nyonih@staff.msu.ac.zw)

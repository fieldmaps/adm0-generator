import logging
import os
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from psycopg import connect

DATABASE = "app"
DATA_URL = "https://data.fieldmaps.io/adm0"
LAND_OSM_URL = (
    "https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip"
)
LAND_USGS_URL = "https://data.fieldmaps.io/adm0/usgs/land/land_polygons.gpkg.zip"
LSIB_URL = "https://data.geodata.state.gov/LSIB.zip"
LSIB_DATE = "2025-02-24"

lands = ["osm", "usgs"]
world_views = ["intl", "all"]
geoms = ["polygons", "lines", "points"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
os.environ["NUMEXPR_MAX_THREADS"] = str(os.cpu_count())

cwd = Path(__file__).parent
data_dir = cwd / "../data"
input_dir = cwd / "../inputs"
output_dir = cwd / "../outputs"
mapshaper = cwd / "../node_modules/mapshaper/bin/mapshaper-xl"


def apply_funcs(prefix, world, *args):
    conn = connect(f"dbname={DATABASE}", autocommit=True)
    for func in args:
        func(conn, prefix, world)
    conn.close()


def get_land_date():
    with open(cwd / "../data/date.txt") as f:
        return f.readline()


def zip_path(file: Path, file_zip: Path):
    file_zip.parent.mkdir(parents=True, exist_ok=True)
    if file.is_file():
        with ZipFile(file_zip, "w", ZIP_DEFLATED) as z:
            z.write(file, file.name)
    if file.is_dir():
        shutil.make_archive(str(file_zip.with_suffix("")), "zip", file)

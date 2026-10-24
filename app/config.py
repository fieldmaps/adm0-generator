"""Pipeline-wide constants and configuration."""

import os
from argparse import ArgumentParser
from logging import INFO, basicConfig
from os import getenv
from pathlib import Path

basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_BOOL_VALS = ("YES", "ON", "TRUE", "1")


def _bool_flag(env_var: str) -> dict:
    return {
        "default": getenv(env_var) in _BOOL_VALS,
        "type": lambda v: v is None or v.upper() in _BOOL_VALS,
        "nargs": "?",
        "const": True,
    }


parser = ArgumentParser(description="Generate ADM0 boundary datasets.")
parser.add_argument("--debug", **_bool_flag("DEBUG"))
parser.add_argument(
    "--step",
    default=getenv("STEP"),
    choices=["_01_download", "_02_prepare", "_03_build", "_04_catalog", "_05_export"],
)
parser.add_argument(
    "--land",
    default=getenv("LAND"),
    choices=["osm", "usgs"],
    help="Process only one land source (default: both). Speeds up iteration.",
)
args = parser.parse_args()

step = args.step
debug = args.debug or step is not None or args.land is not None

# --- XML namespaces for LSIB metadata parsing ---
LSIB_NS = {
    "gco": "http://www.isotc211.org/2005/gco",
    "gmd": "http://www.isotc211.org/2005/gmd",
}

# --- Download URLs ---
DATA_URL = "https://data.fieldmaps.io/adm0"
LAND_OSM_URL = (
    "https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip"
)
LAND_USGS_URL = "https://data.geodata.state.gov/WorldPolygons.zip"
LSIB_URL = "https://data.geodata.state.gov/LSIB.gpkg"
LSIB_META_URL = "https://geodata.state.gov/geonetwork/srv/api/records/3bdb81a0-c1b9-439a-a0b1-85dac30c59b2"

# --- Export options ---
PARQUET_OPTS = "(COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION V2)"
GEOM_PRECISION = 0.000000001
os.environ["OGR_ORGANIZE_POLYGONS"] = "ONLY_CCW"

# --- Pipeline dimensions ---
ALL_LANDS = ("osm", "usgs")
lands = [args.land] if args.land else list(ALL_LANDS)
world_views = ["intl", "all"]
geoms = ["polygons", "lines", "points"]

# --- Output layer definitions: (geom_name, geom_type, table_suffix) ---
EXPORT_LAYERS = [
    ("lines", "MultiLineString", "lines_02"),
    ("points", "Point", "points_01"),
    ("polygons", "MultiPolygon", "polygons_01_a"),
    ("voronoi", "MultiPolygon", "voronoi_01_a"),
]

# --- Intermediate table suffixes dropped after each world-view ---
LAYERS_WORLD = [
    "lines_02",
    "points_01",
    "polygons_01_a",
    "polygons_01_p",
    "voronoi_01_a",
]

# --- Catalog path segments: land -> license folder, world -> view folder ---
LICENSE_DIR = {"usgs": "cc0", "osm": "odbl"}
VIEW_DIR = {"intl": "humanitarian", "all": "disaggregated"}

# --- Directories ---
cwd = Path(__file__).parent
tmp_dir = cwd / "../tmp"
download_dir = tmp_dir / "download"
input_dir = cwd / "../inputs"
output_dir = cwd / "../outputs"
catalog_dir = cwd / "../catalog"

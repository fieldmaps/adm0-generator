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
parser.add_argument(
    "--bounds",
    default=getenv("BOUNDS"),
    choices=["lsib", "gaul"],
    help="Process only one boundary source (default: both).",
)
args = parser.parse_args()

step = args.step
debug = (
    args.debug or step is not None or args.land is not None or args.bounds is not None
)

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
# A land key is the land source, suffixed "_gaul" for the GAUL boundary variant.
ALL_LANDS = ("osm", "usgs")
ALL_BOUNDS = ("lsib", "gaul")
_bounds = [args.bounds] if args.bounds else list(ALL_BOUNDS)
_lands = [args.land] if args.land else list(ALL_LANDS)
lands = [ln if b == "lsib" else f"{ln}_gaul" for b in _bounds for ln in _lands]
world_views = ["intl", "all", "gaul"]


def land_of(key: str) -> str:
    """Return the land source (``osm`` or ``usgs``) of a land key."""
    return key.removesuffix("_gaul")


def bounds_of(key: str) -> str:
    """Return the boundary source (``lsib`` or ``gaul``) of a land key."""
    return "gaul" if key.endswith("_gaul") else "lsib"


def views_of(key: str) -> list[str]:
    """Return the world views built for a land key."""
    return ["gaul"] if bounds_of(key) == "gaul" else ["intl", "all"]


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

# --- Catalog folder per (land key, world view) ---
CATALOG_DIR = {
    ("usgs", "intl"): "cc0/humanitarian",
    ("usgs", "all"): "cc0/disaggregated",
    ("osm", "intl"): "odbl/humanitarian",
    ("osm", "all"): "odbl/disaggregated",
    ("usgs_gaul", "gaul"): "cc-by/gaul",
    ("osm_gaul", "gaul"): "odbl/gaul",
}

# --- Directories ---
cwd = Path(__file__).parent
tmp_dir = cwd / "../tmp"
download_dir = tmp_dir / "download"
input_dir = cwd / "../inputs"
gaul_input_dir = input_dir / "gaul"
output_dir = cwd / "../outputs"
catalog_dir = cwd / "../catalog"

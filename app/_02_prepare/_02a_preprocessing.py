"""Load OSM land, USGS land, and LSIB files into DuckDB."""

import re
import sqlite3
from logging import getLogger
from pathlib import Path

from duckdb import DuckDBPyConnection

from app.config import download_dir
from app.utils import get_source_dates

logger = getLogger(__name__)


def _fix_lsib(conn: DuckDBPyConnection) -> None:
    """Remove known erroneous LSIB segments."""
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SD' AND rank::INTEGER=1")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='KE' AND rank::INTEGER=2")


def _fix_land(conn: DuckDBPyConnection, land: str) -> None:
    """Add wld_update column to land table."""
    osm_date, _ = get_source_dates()
    conn.execute(f"""--sql
        ALTER TABLE "{land}_land_00"
        ADD COLUMN IF NOT EXISTS wld_update DATE DEFAULT '{osm_date}'
    """)


def _load_lsib(conn: DuckDBPyConnection) -> None:
    lsib_path = download_dir / "lsib/LSIB.gpkg"
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS lsib_00 AS SELECT * FROM ST_Read('{lsib_path}')"
    )
    _fix_lsib(conn)


def _load_osm(conn: DuckDBPyConnection) -> None:
    osm_path = next((download_dir / "osm").rglob("land_polygons.shp"))
    conn.execute(
        f"CREATE OR REPLACE TABLE osm_land_00 AS "
        f"SELECT * EXCLUDE OGC_FID FROM ST_Read('{osm_path}')"
    )


def _wp_layer(gpkg: Path) -> str:
    """Return the un-generalized World Polygons layer (e.g. ``DoS_WP_11_4``)."""
    with sqlite3.connect(gpkg) as db:
        return next(
            name
            for (name,) in db.execute(
                "SELECT table_name FROM gpkg_contents WHERE data_type='features'"
            )
            if re.fullmatch(r"DoS_WP_\d+_\d+", name)
        )


def _load_usgs(conn: DuckDBPyConnection) -> None:
    # Caspian Sea is the only DoS_WP_* feature without a WP_Name; filter it out.
    usgs_path = next((download_dir / "usgs").rglob("WorldPolygons*.gpkg"))
    layer = _wp_layer(usgs_path)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE usgs_land_00 AS
        SELECT row_number() OVER () AS "FID", geom
        FROM (
            SELECT UNNEST(ST_Dump(geom)).geom AS geom
            FROM ST_Read('{usgs_path}', layer='{layer}')
            WHERE WP_Name IS NOT NULL
        )
    """)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Load shared LSIB plus the given land source into DuckDB."""
    _load_lsib(conn)
    if land == "osm":
        _load_osm(conn)
    elif land == "usgs":
        _load_usgs(conn)
    _fix_land(conn, land)
    logger.info("preprocessing %s", land)

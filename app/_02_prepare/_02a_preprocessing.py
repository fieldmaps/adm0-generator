"""Load OSM land, USGS land, and LSIB files into DuckDB."""

import re
import sqlite3
from logging import getLogger
from pathlib import Path

from duckdb import DuckDBPyConnection

from app.config import bounds_of, download_dir, land_of
from app.utils import get_source_date

logger = getLogger(__name__)


def _fix_lsib(conn: DuckDBPyConnection) -> None:
    """Remove known erroneous LSIB segments."""
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SD' AND rank::INTEGER=1")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='KE' AND rank::INTEGER=2")


def _fix_land(conn: DuckDBPyConnection, land: str) -> None:
    """Add wld_update column to land table."""
    land_date = get_source_date(land)
    conn.execute(f"""--sql
        ALTER TABLE "{land}_land_00"
        ADD COLUMN IF NOT EXISTS wld_update DATE DEFAULT '{land_date}'
    """)


def _load_lsib(conn: DuckDBPyConnection) -> None:
    lsib_path = download_dir / "lsib/LSIB.gpkg"
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS lsib_00 AS SELECT * FROM ST_Read('{lsib_path}')"
    )
    _fix_lsib(conn)


def _load_osm(conn: DuckDBPyConnection, table: str) -> None:
    osm_path = next((download_dir / "osm").rglob("land_polygons.shp"))
    conn.execute(
        f'CREATE OR REPLACE TABLE "{table}" AS '
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


def _load_usgs(conn: DuckDBPyConnection, table: str) -> None:
    # Caspian Sea is the only DoS_WP_* feature without a WP_Name; filter it out.
    usgs_path = next((download_dir / "usgs").rglob("WorldPolygons*.gpkg"))
    layer = _wp_layer(usgs_path)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{table}" AS
        SELECT row_number() OVER () AS "FID", geom
        FROM (
            SELECT UNNEST(ST_Dump(geom)).geom AS geom
            FROM ST_Read('{usgs_path}', layer='{layer}')
            WHERE WP_Name IS NOT NULL
        )
    """)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Load LSIB (unless GAUL bounds) plus the given land source into DuckDB."""
    if bounds_of(land) == "lsib":
        _load_lsib(conn)
    loader = {"osm": _load_osm, "usgs": _load_usgs}[land_of(land)]
    loader(conn, f"{land}_land_00")
    _fix_land(conn, land)
    logger.info("preprocessing %s", land)

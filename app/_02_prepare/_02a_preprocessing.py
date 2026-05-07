"""Load OSM land, USGS land, and LSIB files into DuckDB."""

from logging import getLogger

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


def _load_usgs(conn: DuckDBPyConnection) -> None:
    usgs_path = download_dir / "usgs/land_polygons.gpkg"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE usgs_land_00 AS
        SELECT row_number() OVER () AS "FID", * FROM ST_Read('{usgs_path}')
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

"""Load OSM land, USGS land, and LSIB files into DuckDB."""

from logging import getLogger
from shutil import rmtree

from duckdb import DuckDBPyConnection

from app.config import download_dir, lands

logger = getLogger(__name__)


def _fix_lsib(conn: DuckDBPyConnection) -> None:
    """Remove known erroneous LSIB segments."""
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SD' AND rank::INTEGER=1")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SS' AND rank::INTEGER=2")
    conn.execute("DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='KE' AND rank::INTEGER=2")


def _fix_land(conn: DuckDBPyConnection, land: str) -> None:
    """Add wld_update column to land table."""
    date = conn.execute("SELECT osm_date FROM dates").fetchall()[0][0]
    conn.execute(f"""--sql
        ALTER TABLE "{land}_land_00"
        ADD COLUMN IF NOT EXISTS wld_update DATE DEFAULT '{date}'
    """)


def main(conn: DuckDBPyConnection) -> None:
    """Load and fix all source layers."""
    osm_path = next((download_dir / "land_osm").rglob("land_polygons.shp"))
    usgs_path = download_dir / "land_usgs/land_polygons.gpkg"
    lsib_path = download_dir / "lsib/LSIB.gpkg"
    conn.execute(
        f"CREATE OR REPLACE TABLE osm_land_00 AS SELECT * EXCLUDE OGC_FID FROM ST_Read('{osm_path}')"
    )
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE usgs_land_00 AS
        SELECT row_number() OVER () AS "FID", * FROM ST_Read('{usgs_path}')
    """)
    conn.execute(
        f"CREATE OR REPLACE TABLE lsib_00 AS SELECT * FROM ST_Read('{lsib_path}')"
    )
    rmtree(download_dir)
    _fix_lsib(conn)
    for land in lands:
        _fix_land(conn, land)
    logger.info("preprocessing")

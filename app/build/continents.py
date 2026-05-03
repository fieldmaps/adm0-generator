"""Identify land masses crossed by boundary lines."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.utils import discard

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Identify land masses crossed by boundary lines."""
    table_in1 = f"{land}_land_00"
    table_in2 = f"{land}_lines_01"
    table_out = f"{land}_land_01"
    rows = conn.execute(f'SELECT ST_AsWKB(geom) FROM "{table_in2}"').fetchall()
    if not rows:
        return
    boundary_wkb = rows[0][0]
    conn.execute(
        f"""--sql
        CREATE OR REPLACE TABLE "{table_out}" AS
        SELECT *
        FROM "{table_in1}" AS a
        WHERE ST_Crosses(a.geom, ST_GeomFromWKB($1))
        """,
        [boundary_wkb],
    )
    discard(conn, table_in2)
    logger.info("%s_continents", land)

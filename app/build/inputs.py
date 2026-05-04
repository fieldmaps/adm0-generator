"""Load adm0 lines and points GeoPackages and append LSIB lines."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import input_dir, tmp_dir
from app.utils import copy_from_db, discard

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Load input lines and points GeoPackages and append LSIB to lines."""
    prepare_db = tmp_dir / f"{land}_prepare.duckdb"
    for table in ["lsib_00", f"{land}_land_00", f"{land}_attributes_points"]:
        copy_from_db(conn, prepare_db, table)
    for layer, file in [
        (f"{land}_lines_00", "adm0_lines.gpkg"),
        (f"{land}_points_00", "adm0_points.gpkg"),
    ]:
        path = input_dir / file
        conn.execute(
            f"CREATE OR REPLACE TABLE \"{layer}\" AS SELECT * FROM ST_Read('{path}')"
        )
    cols = [row[0] for row in conn.execute(f'DESCRIBE "{land}_lines_00"').fetchall()]
    col_list = ", ".join(f'"{c}"' for c in cols)
    conn.execute(f'INSERT INTO "{land}_lines_00" SELECT {col_list} FROM lsib_00')
    discard(conn, "lsib_00")
    logger.info("%s_inputs", land)

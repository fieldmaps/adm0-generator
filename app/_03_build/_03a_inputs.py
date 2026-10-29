"""Load adm0 lines and points, plus LSIB lines for the LSIB variant."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import bounds_of, gaul_input_dir, input_dir, tmp_dir
from app.utils import copy_from_db, discard

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Load input lines and points, appending LSIB to lines unless GAUL bounds."""
    prepare_db = tmp_dir / f"{land}__02_prepare.duckdb"
    is_gaul = bounds_of(land) == "gaul"
    tables = [f"{land}_land_00", f"{land}_attributes_points"]
    for table in tables if is_gaul else ["lsib_00", *tables]:
        copy_from_db(conn, prepare_db, table)
    src_dir = gaul_input_dir if is_gaul else input_dir
    for layer, file in [
        (f"{land}_lines_00", "adm0_lines.parquet"),
        (f"{land}_points_00", "adm0_points.parquet"),
    ]:
        path = src_dir / file
        conn.execute(
            f"CREATE OR REPLACE TABLE \"{layer}\" AS SELECT * FROM read_parquet('{path}')"
        )
    if not is_gaul:
        cols = [r[0] for r in conn.execute(f'DESCRIBE "{land}_lines_00"').fetchall()]
        col_list = ", ".join(f'"{c}"' for c in cols)
        conn.execute(f'INSERT INTO "{land}_lines_00" SELECT {col_list} FROM lsib_00')
        discard(conn, "lsib_00")
    logger.info("%s_inputs", land)

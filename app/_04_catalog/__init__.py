"""Catalog stage modules."""

from app.config import debug, tmp_dir, views_of
from app.utils import copy_from_db, export_debug_tables, get_conn

from . import (
    _04a_lines,
    _04b_polygons,
    _04c_points,
    _04d_parquet,
    _04e_validate,
    _04f_cleanup,
    _04g_portolan,
)


def main(land: str) -> None:
    """Run the catalog stage for one land source."""
    conn = get_conn("_04_catalog", land)
    prepare_db = tmp_dir / f"{land}__02_prepare.duckdb"
    build_db = tmp_dir / f"{land}__03_build.duckdb"
    for table in [f"{land}_attributes_points", f"{land}_attributes_lines"]:
        copy_from_db(conn, prepare_db, table)
    for table in [
        f"{land}_land_01",
        f"{land}_lines_00",
        f"{land}_polygons_00",
        f"{land}_voronoi_00",
    ]:
        copy_from_db(conn, build_db, table)
    for world in views_of(land):
        _04a_lines.main(conn, land, world)
        _04b_polygons.main(conn, land, world)
        _04c_points.main(conn, land, world)
        _04d_parquet.main(conn, land, world)
        _04e_validate.main(conn, land, world)
        _04f_cleanup.main(conn, land, world)
    _04g_portolan.main(conn, land)
    if debug:
        export_debug_tables(conn, "_04_catalog", land)
    conn.close()


def finalize() -> None:
    """Validate the catalog after all lands processed."""
    _04g_portolan.finalize()

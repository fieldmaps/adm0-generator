"""Export stage modules."""

from app.config import debug, world_views
from app.utils import export_debug_tables, get_conn

from . import (
    _04a_lines,
    _04b_polygons,
    _04c_points,
    _04d_outputs,
    _04e_cleanup,
    _04f_meta,
)


def main(land: str) -> None:
    """Run the export stage for one land source."""
    conn = get_conn("_04_export", land)
    for world in world_views:
        _04a_lines.main(conn, land, world)
        _04b_polygons.main(conn, land, world)
        _04c_points.main(conn, land, world)
        _04d_outputs.main(conn, land, world)
        _04e_cleanup.main(conn, land, world)
    if debug:
        export_debug_tables(conn, "_04_export", land)
    conn.close()


def finalize() -> None:
    """Write metadata after all lands processed."""
    _04f_meta.main()

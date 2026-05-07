"""Export stage modules."""

from app.config import debug, world_views
from app.utils import export_debug_tables, get_conn

from . import (
    _04a_outputs_land,
    _04b_lines,
    _04c_polygons,
    _04d_points,
    _04e_outputs,
    _04f_cleanup,
    _04g_meta,
)


def main(land: str) -> None:
    """Run the export stage for one land source."""
    conn = get_conn("_04_export", land)
    _04a_outputs_land.main(conn, land)
    for world in world_views:
        _04b_lines.main(conn, land, world)
        _04c_polygons.main(conn, land, world)
        _04d_points.main(conn, land, world)
        _04e_outputs.main(conn, land, world)
        _04f_cleanup.main(conn, land, world)
    _04f_cleanup.postprocessing_land(conn, land)
    if debug:
        export_debug_tables(conn, "_04_export", land)
    conn.close()


def finalize() -> None:
    """Write metadata after all lands processed."""
    _04g_meta.main()

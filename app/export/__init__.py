"""Export stage modules."""

from app.config import debug, lands, world_views
from app.utils import export_debug_tables, get_conn

from . import cleanup, lines, meta, outputs, outputs_land, points, polygons


def main() -> None:
    """Run the export stage."""
    conn = get_conn("export")
    for land in lands:
        outputs_land.main(conn, land)
        for world in world_views:
            lines.main(conn, land, world)
            polygons.main(conn, land, world)
            points.main(conn, land, world)
            outputs.main(conn, land, world)
            cleanup.main(conn, land, world)
        cleanup.postprocessing_land(conn, land)
    cleanup.postprocessing(conn)
    meta.main()
    if debug:
        export_debug_tables(conn, "export")
    conn.close()

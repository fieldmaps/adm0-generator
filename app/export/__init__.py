"""Export stage modules."""

from app.config import debug, world_views
from app.utils import export_debug_tables, get_conn

from . import cleanup, lines, meta, outputs, outputs_land, points, polygons


def main(land: str) -> None:
    """Run the export stage for one land source."""
    conn = get_conn("export", land)
    outputs_land.main(conn, land)
    for world in world_views:
        lines.main(conn, land, world)
        polygons.main(conn, land, world)
        points.main(conn, land, world)
        outputs.main(conn, land, world)
        cleanup.main(conn, land, world)
    cleanup.postprocessing_land(conn, land)
    if debug:
        export_debug_tables(conn, "export", land)
    conn.close()


def finalize() -> None:
    """Write metadata after all lands processed."""
    meta.main()

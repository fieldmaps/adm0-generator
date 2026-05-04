"""Build stage modules."""

from app.config import debug
from app.utils import export_debug_tables, get_conn

from . import continents, inputs, intersection, polygonize


def main(land: str) -> None:
    """Run the build stage for one land source."""
    conn = get_conn("build", land)
    inputs.main(conn, land)
    polygonize.main(conn, land)
    continents.main(conn, land)
    intersection.main(conn, land)
    if debug:
        export_debug_tables(conn, "build", land)
    conn.close()

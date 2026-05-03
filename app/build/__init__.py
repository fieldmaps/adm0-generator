"""Build stage modules."""

from app.config import debug, lands
from app.utils import export_debug_tables, get_conn

from . import continents, inputs, intersection, polygonize


def main() -> None:
    """Run the build stage."""
    conn = get_conn("build")
    for land in lands:
        inputs.main(conn, land)
        polygonize.main(conn, land)
        continents.main(conn, land)
        intersection.main(conn, land)
    if debug:
        export_debug_tables(conn, "build")
    conn.close()

"""Build stage modules."""

from app.config import debug
from app.utils import export_debug_tables, get_conn

from . import _03a_inputs, _03b_polygonize, _03c_continents, _03d_intersection


def main(land: str) -> None:
    """Run the build stage for one land source."""
    conn = get_conn("_03_build", land)
    _03a_inputs.main(conn, land)
    _03b_polygonize.main(conn, land)
    _03c_continents.main(conn, land)
    _03d_intersection.main(conn, land)
    if debug:
        export_debug_tables(conn, "_03_build", land)
    conn.close()

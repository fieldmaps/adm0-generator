"""Prepare stage modules."""

from logging import getLogger

from app.config import debug
from app.dates import get_source_dates
from app.utils import export_debug_tables, get_conn

from . import attributes, preprocessing

logger = getLogger(__name__)


def main(land: str) -> None:
    """Run the prepare stage for one land source."""
    osm_date, lsib_date = get_source_dates()
    logger.info("dates: osm=%s lsib=%s", osm_date, lsib_date)
    conn = get_conn("prepare", land)
    preprocessing.main(conn, land)
    attributes.main(conn, land)
    if debug:
        export_debug_tables(conn, "prepare", land)
    conn.close()

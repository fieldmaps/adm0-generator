"""Prepare stage modules."""

from logging import getLogger

from app.config import bounds_of, debug
from app.utils import export_debug_tables, get_conn, get_source_date

from . import _02a_preprocessing, _02b_attributes

logger = getLogger(__name__)


def main(land: str) -> None:
    """Run the prepare stage for one land source."""
    logger.info(
        "dates: %s=%s %s=%s",
        land,
        get_source_date(land),
        bounds_of(land),
        get_source_date(bounds_of(land)),
    )
    conn = get_conn("_02_prepare", land)
    _02a_preprocessing.main(conn, land)
    _02b_attributes.main(conn, land)
    if debug:
        export_debug_tables(conn, "_02_prepare", land)
    conn.close()

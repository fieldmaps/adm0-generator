"""Prepare stage modules."""

from app.config import debug, lands
from app.utils import export_debug_tables, get_conn

from . import attributes, dates, download, preprocessing


def main() -> None:
    """Run the prepare stage."""
    conn = get_conn("prepare")
    dates.main(conn)
    download.main()
    preprocessing.main(conn)
    for land in lands:
        attributes.main(conn, land)
    if debug:
        export_debug_tables(conn, "prepare")
    conn.close()

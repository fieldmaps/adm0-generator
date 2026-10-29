"""Export stage modules."""

from app.config import views_of
from app.utils import get_conn

from . import _05a_outputs, _05b_meta


def main(land: str) -> None:
    """Derive download formats from the catalog GeoParquet for one land source."""
    conn = get_conn("_05_export", land)
    for world in views_of(land):
        _05a_outputs.main(conn, land, world)
    conn.close()


def finalize() -> None:
    """Write metadata after all lands processed."""
    _05b_meta.main()

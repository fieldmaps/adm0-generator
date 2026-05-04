"""Read source publication dates from the download cache."""

from app.config import download_dir


def get_source_dates() -> tuple[str, str]:
    """Return ``(osm_date, lsib_date)`` as ISO date strings."""
    osm_date = (download_dir / "osm/.date").read_text().strip()
    lsib_date = (download_dir / "lsib/.date").read_text().strip()
    return osm_date, lsib_date

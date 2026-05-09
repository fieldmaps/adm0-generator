"""Download OSM land polygons, USGS land polygons, and LSIB boundary lines.

Always fetches fresh data. Source publication dates are captured atomically
with each download (OSM Last-Modified header, LSIB metadata XML) and written
to ``tmp/download/{osm,lsib}/.date``.
"""

from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from logging import getLogger
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from httpx import Client, Timeout

from app.config import (
    LAND_OSM_URL,
    LAND_USGS_URL,
    LSIB_META_URL,
    LSIB_NS,
    LSIB_URL,
    download_dir,
)

logger = getLogger(__name__)


def _stream_to_file(dest: Path, url: str) -> None:
    with (
        Client(http2=True, timeout=Timeout(60, connect=30)) as client,
        client.stream("GET", url) as r,
    ):
        r.raise_for_status()
        with dest.open("wb") as f:
            f.writelines(r.iter_bytes(chunk_size=4 * 1024 * 1024))


def _download_zip(output: Path, url: str) -> None:
    tmp = output / ".tmp"
    try:
        _stream_to_file(tmp, url)
        with ZipFile(tmp) as z:
            z.extractall(output)
    finally:
        tmp.unlink(missing_ok=True)


def _download_file(output: Path, url: str) -> None:
    _stream_to_file(output / Path(url).name, url)


def _fetch_lsib(lsib: Path) -> None:
    with Client(http2=True, timeout=Timeout(60, connect=30)) as client:
        r = client.get(LSIB_META_URL, headers={"Accept": "application/xml"})
        r.raise_for_status()
    el = ET.fromstring(r.text).find(  # noqa: S314
        ".//gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date", LSIB_NS
    )
    if el is None or el.text is None:
        msg = "LSIB date not found in metadata response"
        raise ValueError(msg)
    _download_file(lsib, LSIB_URL)
    (lsib / ".date").write_text(el.text)


def _fetch_osm(osm: Path) -> None:
    with Client(http2=True, timeout=Timeout(60, connect=30)) as client:
        r = client.head(LAND_OSM_URL)
        r.raise_for_status()
        last_modified = r.headers.get("last-modified")
    if not last_modified:
        msg = "OSM land date not found in Last-Modified response header"
        raise ValueError(msg)
    date = parsedate_to_datetime(last_modified).date().isoformat()
    _download_zip(osm, LAND_OSM_URL)
    (osm / ".date").write_text(date)


def _fetch_usgs(usgs: Path) -> None:
    _download_zip(usgs, LAND_USGS_URL)
    inner = next(usgs.rglob("WorldPolygon*.zip"))
    with ZipFile(inner) as z:
        z.extractall(usgs)
    inner.unlink()


def main() -> None:
    """Download required input datasets."""
    osm = download_dir / "osm"
    usgs = download_dir / "usgs"
    lsib = download_dir / "lsib"
    for d in [osm, usgs, lsib]:
        d.mkdir(parents=True, exist_ok=True)

    jobs = [(_fetch_lsib, lsib), (_fetch_osm, osm), (_fetch_usgs, usgs)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(fn, arg) for fn, arg in jobs]
    for f in futures:
        f.result()
    logger.info("download: %d fetched", len(jobs))

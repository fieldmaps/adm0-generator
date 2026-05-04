"""Download OSM land polygons, USGS land polygons, and LSIB boundary lines.

Idempotent per source: a source is fetched only when its expected extracted
file (and, for OSM/LSIB, its sibling ``.date`` stamp) is missing from
``tmp/download/``. Source publication dates are captured atomically with the
download so a cached file and its date never drift apart. To force a refresh,
delete the cache (``rm -rf tmp/download/``) or just one source subdir.
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


def _lsib_cached(lsib: Path) -> bool:
    return (lsib / "LSIB.gpkg").exists() and (lsib / ".date").exists()


def _osm_cached(osm: Path) -> bool:
    return (
        next(osm.rglob("land_polygons.shp"), None) is not None
        and (osm / ".date").exists()
    )


def _usgs_cached(usgs: Path) -> bool:
    return (usgs / "land_polygons.gpkg").exists()


def main() -> None:
    """Download required input datasets, skipping any that are already cached."""
    osm = download_dir / "osm"
    usgs = download_dir / "usgs"
    lsib = download_dir / "lsib"
    for d in [osm, usgs, lsib]:
        d.mkdir(parents=True, exist_ok=True)

    jobs = []
    cached = 0
    if _lsib_cached(lsib):
        cached += 1
    else:
        jobs.append((_fetch_lsib, lsib))
    if _osm_cached(osm):
        cached += 1
    else:
        jobs.append((_fetch_osm, osm))
    if _usgs_cached(usgs):
        cached += 1
    else:
        jobs.append((_fetch_usgs, usgs))

    if jobs:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = [pool.submit(fn, arg) for fn, arg in jobs]
        for f in futures:
            f.result()
    logger.info("download: %d fetched, %d cached", len(jobs), cached)

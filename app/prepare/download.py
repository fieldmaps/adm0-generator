"""Download OSM land polygons, USGS land polygons, and LSIB boundary lines."""

from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile

from httpx import Client, Timeout

from app.config import LAND_OSM_URL, LAND_USGS_URL, LSIB_URL, download_dir

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


def main() -> None:
    """Download all required input datasets."""
    rmtree(download_dir, ignore_errors=True)
    land_osm = download_dir / "land_osm"
    land_usgs = download_dir / "land_usgs"
    lsib = download_dir / "lsib"
    for d in [land_osm, land_usgs, lsib]:
        d.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(_download_file, lsib, LSIB_URL),
            pool.submit(_download_zip, land_osm, LAND_OSM_URL),
            pool.submit(_download_zip, land_usgs, LAND_USGS_URL),
        ]
    for f in futures:
        f.result()
    logger.info("download")

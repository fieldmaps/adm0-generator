import logging
import os
from io import BytesIO
from zipfile import ZipFile

import httpx

from .utils import LAND_OSM_URL, LAND_USGS_URL, LSIB_URL, input_dir

logger = logging.getLogger(__name__)


def unzip(output, name, content):
    with ZipFile(content) as z:
        for member in z.infolist():
            if os.path.basename(member.filename):
                member.filename = (
                    name + "." + os.path.basename(member.filename).split(".")[-1]
                ).lower()
                z.extract(member=member, path=output)


def download_zip(output, name, url):
    r = httpx.get(url)
    content = BytesIO(r.content)
    unzip(output, name, content)
    zipfile = output / f"{name}.zip"
    if zipfile.is_file():
        unzip(output, name, output / f"{name}.zip")
        zipfile.unlink()


def get_shp(dir, name, url):
    inputs = input_dir / dir
    inputs.mkdir(exist_ok=True, parents=True)
    dbf = (inputs / f"{name}.dbf").is_file()
    prj = (inputs / f"{name}.prj").is_file()
    shp = (inputs / f"{name}.shp").is_file()
    shx = (inputs / f"{name}.shx").is_file()
    if not dbf or not prj or not shp or not shx:
        download_zip(inputs, name, url)


def main():
    get_shp("lsib", "lsib", LSIB_URL)
    get_shp("land", "land_osm", LAND_OSM_URL)
    if not (input_dir / "land/land_usgs.gpkg").is_file():
        download_zip(input_dir / "land", "land_usgs", LAND_USGS_URL)
    logger.info("download")

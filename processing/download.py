import os
import requests
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from .utils import logging, LAND_URL, SIMPLE_LAND_URL, LSIB_URL

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs')


def download_zip(url, output):
    r = requests.get(url)
    with ZipFile(BytesIO(r.content)) as z:
        for member in z.infolist():
            member.filename = os.path.basename(member.filename)
            z.extract(member=member, path=output)


def get_shp(dir, name, url):
    inputs = (input_dir / dir)
    inputs.mkdir(exist_ok=True, parents=True)
    cpg = (inputs / f'{name}.cpg').is_file()
    dbf = (inputs / f'{name}.dbf').is_file()
    prj = (inputs / f'{name}.prj').is_file()
    shp = (inputs / f'{name}.shp').is_file()
    shx = (inputs / f'{name}.shx').is_file()
    if not cpg or not dbf or not prj or not shp or not shx:
        download_zip(url, inputs)


def main():
    get_shp('lsib', 'LSIB', LSIB_URL)
    get_shp('land', 'simplified_land_polygons', SIMPLE_LAND_URL)
    get_shp('land', 'land_polygons', LAND_URL)
    logger.info('download')

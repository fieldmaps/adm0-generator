import os
import requests
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from processing.utils import logging, LSIB_URL, LAND_URL, SIMPLE_LAND_URL

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = cwd / '../inputs'


def download_zip(url, name, output):
    r = requests.get(url)
    with ZipFile(BytesIO(r.content)) as z:
        for member in z.infolist():
            if os.path.basename(member.filename):
                member.filename = (
                    name + '.' + os.path.basename(member.filename).split('.')[-1]).lower()
                z.extract(member=member, path=output)


def get_shp(dir, name, url):
    inputs = input_dir / dir
    inputs.mkdir(exist_ok=True, parents=True)
    dbf = (inputs / f'{name}.dbf').is_file()
    prj = (inputs / f'{name}.prj').is_file()
    shp = (inputs / f'{name}.shp').is_file()
    shx = (inputs / f'{name}.shx').is_file()
    if not dbf or not prj or not shp or not shx:
        download_zip(url, name, inputs)


def main():
    get_shp('lsib', 'lsib', LSIB_URL)
    get_shp('land', 'simplified_land_polygons', SIMPLE_LAND_URL)
    get_shp('land', 'land_polygons', LAND_URL)
    logger.info('download')

import os
import requests
from zipfile import ZipFile
from io import BytesIO
from .utils import logging, ADM0_URL, LAND_URL

logger = logging.getLogger(__name__)


def get_file(url, output):
    r = requests.get(url)
    with open(output, 'wb') as f:
        f.write(r.content)
    logger.info(url)


def get_zip(url, output):
    r = requests.get(url)
    with ZipFile(BytesIO(r.content)) as z:
        for member in z.infolist():
            member.filename = os.path.basename(member.filename)
            z.extract(member=member, path=output)
    logger.info(url)


def main(inputs):
    adm0_lines = (inputs / 'adm0/adm0_lines.gpkg')
    adm0_points = (inputs / 'adm0/adm0_points.gpkg')
    adm0_attributes = (inputs / 'adm0/adm0_attributes.xlsx')
    land_cpg = (inputs / 'land/land_polygons.cpg').is_file()
    land_dbf = (inputs / 'land/land_polygons.dbf').is_file()
    land_prj = (inputs / 'land/land_polygons.prj').is_file()
    land_shp = (inputs / 'land/land_polygons.shp').is_file()
    land_shx = (inputs / 'land/land_polygons.shx').is_file()
    if not adm0_lines.is_file():
        get_file(f'{ADM0_URL}/adm0_lines.gpkg', adm0_lines)
    if not adm0_points.is_file():
        get_file(f'{ADM0_URL}/adm0_points.gpkg', adm0_points)
    if not adm0_attributes.is_file():
        get_file(f'{ADM0_URL}/adm0_attributes.xlsx', adm0_attributes)
    if not land_cpg or not land_dbf or not land_prj or not land_shp or not land_shx:
        get_zip(LAND_URL, inputs / 'land')

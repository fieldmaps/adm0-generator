import os
import requests
from zipfile import ZipFile
from io import BytesIO
from .utils import logging, LAND_POLYGONS_URL

logger = logging.getLogger(__name__)


def main(output):
    r = requests.get(LAND_POLYGONS_URL)
    with ZipFile(BytesIO(r.content)) as z:
        for member in z.infolist():
            member.filename = os.path.basename(member.filename)
            z.extract(member=member, path=output)
    logger.info(f'land_polygons')

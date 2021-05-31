import os
import requests
from zipfile import ZipFile
from io import BytesIO
from .utils import logging

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

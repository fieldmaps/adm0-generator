import subprocess
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)


def main(name, file):
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-dim', 'XY',
        '-t_srs', 'EPSG:4326',
        '-lco', 'FID=fid',
        '-lco', 'GEOMETRY_NAME=geom',
        '-nln', f'{name}_00',
        '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
        file,
    ])
    logger.info(name)

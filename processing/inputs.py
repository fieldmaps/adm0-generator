import subprocess
from pathlib import Path
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = cwd / '../inputs/lsib_extension'


def main(_, prefix, __):
    layers = [
        (f'{prefix}lines', 'adm0_lines.gpkg'),
        (f'{prefix}points', 'adm0_points.gpkg'),
    ]
    for l, file in layers:
        subprocess.run([
            'ogr2ogr',
            '-overwrite',
            '-makevalid',
            '-dim', 'XY',
            '-t_srs', 'EPSG:4326',
            '-nlt', 'PROMOTE_TO_MULTI',
            '-lco', 'FID=fid',
            '-lco', 'GEOMETRY_NAME=geom',
            '-nln', f'{l}_00',
            '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
            (input_dir / file),
        ])
        if l == f'{prefix}lines':
            subprocess.run([
                'ogr2ogr',
                '-append',
                '-nln', f'{prefix}lines_00',
                '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
                f'PG:dbname={DATABASE}', 'lsib_00',
            ])
    logger.info(prefix)

import subprocess
from pathlib import Path
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs').resolve()


def main(_, name, prefix):
    layer = f'{prefix}{name}'
    layers = [
        (f'{layer}_lines', f'{name}/adm0_lines.gpkg'),
        (f'{layer}_points', f'{name}/adm0_points.gpkg'),
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
        if l == f'{prefix}open_lines':
            subprocess.run([
                'ogr2ogr',
                '-append',
                '-nln', f'{prefix}open_lines_00',
                '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
                f'PG:dbname={DATABASE}', 'lsib_00',
            ])
    logger.info(layer)

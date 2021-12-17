import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent

layers = [
    ('lines', 'lines_02'),
    ('points', 'points_01'),
    ('polygons', 'polygons_02_a'),
]


def main(_, prefix, world):
    output_dir = cwd / f'../outputs/{world}'
    output_dir.mkdir(exist_ok=True, parents=True)
    for n, l in layers:
        file_name = f'{prefix}adm0_{n}'
        gpkg = output_dir / f'{file_name}.gpkg'
        gpkg.unlink(missing_ok=True)
        subprocess.run([
            'ogr2ogr',
            '-overwrite',
            '-makevalid',
            '-nln', file_name,
            gpkg,
            f'PG:dbname={DATABASE}', f'{prefix}{l}_{world}',
        ])
        file_zip = (output_dir / f'{file_name}.gpkg.zip')
        file_zip.unlink(missing_ok=True)
        with ZipFile(file_zip, 'w', ZIP_DEFLATED) as z:
            z.write(gpkg, gpkg.name)
        gpkg.unlink(missing_ok=True)
    logger.info(f'{prefix}{world}')

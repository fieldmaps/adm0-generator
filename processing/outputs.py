import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
output_dir = (cwd / '../outputs').resolve()

layers = [
    ('polygons', 'polygons_01'),
    ('lines', 'lines_02'),
    ('points', 'points_01'),
]


def main(_, name, prefix):
    layer = f'{prefix}{name}'
    for n, l in layers:
        file = (output_dir / f'{name}/{prefix}adm0_{n}.gpkg')
        file.unlink(missing_ok=True)
        subprocess.run([
            'ogr2ogr',
            '-overwrite',
            '-makevalid',
            file,
            f'PG:dbname={DATABASE}', f'{layer}_{l}',
        ])
        file_zip = (output_dir / f'{name}/{prefix}adm0_{n}.gpkg.zip')
        file_zip.unlink(missing_ok=True)
        with ZipFile(file_zip, 'w', ZIP_DEFLATED) as z:
            z.write(file, file.name)
        file.unlink(missing_ok=True)
    logger.info(layer)

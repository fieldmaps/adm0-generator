import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .utils import DATABASE, logging

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent


def main(prefix):
    output_dir = cwd / f'../outputs/land'
    output_dir.mkdir(exist_ok=True, parents=True)
    file_name = f'{prefix}land_polygons'
    gpkg = output_dir / f'{file_name}.gpkg'
    gpkg.unlink(missing_ok=True)
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-makevalid',
        '-nln', file_name,
        gpkg,
        f'PG:dbname={DATABASE}', f'{prefix}land_00',
    ])
    file_zip = (output_dir / f'{file_name}.gpkg.zip')
    file_zip.unlink(missing_ok=True)
    with ZipFile(file_zip, 'w', ZIP_DEFLATED) as z:
        z.write(gpkg, gpkg.name)
    gpkg.unlink(missing_ok=True)
    logger.info(f'{prefix}land')

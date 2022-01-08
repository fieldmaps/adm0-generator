import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .utils import DATABASE, logging

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent


def output_gpkg(prefix, output_dir, file_name, gpkg):
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-makevalid',
        '-nln', file_name,
        gpkg,
        f'PG:dbname={DATABASE}', f'{prefix}land_00',
    ])
    gpkg_zip = output_dir / f'{file_name}.gpkg.zip'
    gpkg_zip.unlink(missing_ok=True)
    with ZipFile(gpkg_zip, 'w', ZIP_DEFLATED) as z:
        z.write(gpkg, gpkg.name)


def output_shp(prefix, output_dir, file_name):
    exts = ['cpg', 'dbf', 'prj', 'shp', 'shx']
    shp = output_dir / f'{file_name}.shp'
    subprocess.run([
        'pgsql2shp', '-k', '-q',
        '-f', shp,
        DATABASE, f'{prefix}land_00',
    ])
    shp_zip = output_dir / f'{file_name}.shp.zip'
    shp_zip.unlink(missing_ok=True)
    with ZipFile(shp_zip, 'w', ZIP_DEFLATED) as z:
        for ext in exts:
            shp_part = output_dir / f'{file_name}.{ext}'
            z.write(shp_part, shp_part.name)
            shp_part.unlink(missing_ok=True)


def main(prefix):
    data_dir = cwd / f'../data/land'
    data_dir.mkdir(exist_ok=True, parents=True)
    output_dir = cwd / f'../outputs/land'
    output_dir.mkdir(exist_ok=True, parents=True)
    file_name = f'{prefix}land_polygons'
    gpkg = data_dir / f'{file_name}.gpkg'
    gpkg.unlink(missing_ok=True)
    output_gpkg(prefix, output_dir, file_name, gpkg)
    output_shp(prefix, output_dir, file_name)
    if prefix == 'simplified_':
        gpkg.unlink(missing_ok=True)
    logger.info(f'{prefix}land')

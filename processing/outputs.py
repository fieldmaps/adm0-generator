import subprocess
from pathlib import Path
from psycopg.sql import SQL, Identifier
from zipfile import ZipFile, ZIP_DEFLATED
from processing.utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent

layers = [
    ('lines', 'lines_02'),
    ('points', 'points_01'),
    ('polygons', 'polygons_01_a'),
    ('voronoi', 'voronoi_01_a'),
    ('clip', 'polygons_01_p'),
]

query_1 = """
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS id;
"""


def output_gpkg(prefix, layer, wld, geom, output_dir, file_name, gpkg, id):
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-makevalid',
        '-sql', f'SELECT * FROM {prefix}{layer}_{wld} ORDER BY {id}',
        '-nln', file_name,
        gpkg,
        f'PG:dbname={DATABASE}',
    ])
    if geom in ['clip', 'voronoi']:
        return
    gpkg_zip = output_dir / f'{file_name}.gpkg.zip'
    gpkg_zip.unlink(missing_ok=True)
    with ZipFile(gpkg_zip, 'w', ZIP_DEFLATED) as z:
        z.write(gpkg, gpkg.name)


def output_shp(prefix, layer, wld, output_dir, file_name, id):
    shp = output_dir / f'{file_name}.shp'
    subprocess.run([
        'pgsql2shp', '-k', '-q',
        '-f', shp,
        DATABASE,
        f'SELECT * FROM {prefix}{layer}_{wld} ORDER BY {id}',
    ])
    shp_zip = output_dir / f'{file_name}.shp.zip'
    shp_zip.unlink(missing_ok=True)
    with ZipFile(shp_zip, 'w', ZIP_DEFLATED) as z:
        for ext in ['cpg', 'dbf', 'prj', 'shp', 'shx']:
            shp_part = output_dir / f'{file_name}.{ext}'
            z.write(shp_part, shp_part.name)
            shp_part.unlink(missing_ok=True)


def output_xlsx(gpkg, output_dir, file_name):
    xlsx = output_dir / f'{file_name}.xlsx'
    xlsx.unlink(missing_ok=True)
    subprocess.run(['ogr2ogr', xlsx, gpkg])


def outputs(conn, prefix, wld, geom, layer):
    if geom in ['clip', 'voronoi'] and prefix == 'simplified_':
        return
    data_dir = cwd / f'../data/{wld}'
    data_dir.mkdir(exist_ok=True, parents=True)
    output_dir = cwd / f'../outputs/{wld}'
    output_dir.mkdir(exist_ok=True, parents=True)
    file_name = f'{prefix}adm0_{geom}'
    gpkg = data_dir / f'{file_name}.gpkg'
    gpkg.unlink(missing_ok=True)
    conn.execute(SQL(query_1).format(
        table_out=Identifier(f'{prefix}{layer}_{wld}'),
    ))
    id = 'fid' if geom == 'lines' else 'adm0_id'
    output_gpkg(prefix, layer, wld, geom, output_dir, file_name, gpkg, id)
    if geom in ['clip', 'voronoi']:
        return
    output_shp(prefix, layer, wld, output_dir, file_name, id)
    output_xlsx(gpkg, output_dir, file_name)
    if prefix == 'simplified_':
        gpkg.unlink(missing_ok=True)


def main(conn, prefix, wld):
    for geom, layer in layers:
        outputs(conn, prefix, wld, geom, layer)
    logger.info(f'{prefix}{wld}')

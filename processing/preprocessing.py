import subprocess
from pathlib import Path
from psycopg import connect
from psycopg.sql import SQL, Identifier, Literal
from processing.utils import logging, DATABASE, get_land_date

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs').resolve()


def import_layers():
    layers = [
        ('osm_land_00', 'land/land_osm.shp'),
        ('usgs_land_00', 'land/land_usgs.gpkg'),
        ('lsib_00', 'lsib/lsib.shp'),
    ]
    for layer, file in layers:
        subprocess.run([
            'ogr2ogr',
            '-overwrite',
            '-makevalid',
            '-dim', 'XY',
            '-t_srs', 'EPSG:4326',
            '-nlt', 'PROMOTE_TO_MULTI',
            '-lco', 'FID=fid',
            '-lco', 'GEOMETRY_NAME=geom',
            '-nln', layer,
            '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
            (input_dir / file),
        ])


def fix_lsib(conn):
    query_1 = "DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SD' AND rank=1;"
    query_2 = "DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='SS' AND rank=2;"
    query_3 = "DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SS' AND rank=2;"
    query_4 = "DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='KE' AND rank=2;"
    conn.execute(SQL(query_1))
    conn.execute(SQL(query_2))
    conn.execute(SQL(query_3))
    conn.execute(SQL(query_4))


def fix_land(conn, land):
    query_1 = """
        ALTER TABLE {table_out}
        ADD COLUMN date DATE DEFAULT {date};
    """
    conn.execute(SQL(query_1).format(
        date=Literal(get_land_date()),
        table_out=Identifier(f'{land}_land_00'),
    ))


def main():
    conn = connect(f'dbname={DATABASE}', autocommit=True)
    import_layers()
    fix_lsib(conn)
    fix_land(conn, 'osm')
    fix_land(conn, 'usgs')
    conn.close()
    logger.info('preprocessing')

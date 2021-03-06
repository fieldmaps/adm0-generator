import subprocess
from pathlib import Path
from psycopg2 import connect
from psycopg2.sql import SQL, Identifier, Literal
from .utils import logging, DATABASE, get_land_date

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs').resolve()


def import_layers():
    layers = [
        ('land_00', 'land/land_polygons.shp'),
        ('simplified_land_00_tmp1', 'land/simplified_land_polygons.shp'),
        ('lsib_00', 'lsib/LSIB.shp'),
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


def fix_lsib(cur):
    query_1 = "DELETE FROM lsib_00 WHERE cc1='CN' AND cc2='IN' AND rank=1;"
    query_2 = "DELETE FROM lsib_00 WHERE cc1='KE' AND cc2='SS' AND rank=2;"
    query_3 = "DELETE FROM lsib_00 WHERE cc1='SS' AND cc2='SD' AND rank=1;"
    cur.execute(SQL(query_1))
    cur.execute(SQL(query_2))
    cur.execute(SQL(query_3))


def fix_land(cur):
    query_1 = """
        ALTER TABLE {table_out}
        ADD COLUMN date DATE DEFAULT {date};
    """
    cur.execute(SQL(query_1).format(
        date=Literal(get_land_date()),
        table_out=Identifier('land_00'),
    ))


def fix_land_simple(cur):
    query_1 = """
        DROP TABLE IF EXISTS {table_out};
        CREATE TABLE {table_out} AS
        SELECT
            ST_Multi(ST_MakeEnvelope(
                -180, -90, 180, -85, 4326
            ))::GEOMETRY(MultiPolygon, 4326) AS geom
        FROM {table_in}
        UNION ALL
        SELECT geom
        FROM {table_in};
    """
    query_2 = """
        DROP TABLE IF EXISTS {table_out};
        CREATE TABLE {table_out} AS
        SELECT
            (ST_Dump(
                ST_Union(geom)
            )).geom::GEOMETRY(Polygon, 4326) AS geom
        FROM {table_in};
        CREATE INDEX ON {table_out} USING GIST(geom);
    """
    query_3 = """
        ALTER TABLE {table_out}
        ADD COLUMN date DATE DEFAULT {date};
    """
    cur.execute(SQL(query_1).format(
        table_in=Identifier('simplified_land_00_tmp1'),
        table_out=Identifier('simplified_land_00_tmp2'),
    ))
    cur.execute(SQL(query_2).format(
        table_in=Identifier('simplified_land_00_tmp2'),
        table_out=Identifier('simplified_land_00'),
    ))
    cur.execute(SQL(query_3).format(
        date=Literal(get_land_date()),
        table_out=Identifier('simplified_land_00'),
    ))


def cleanup_tmp(cur):
    query_1 = """
        DROP TABLE IF EXISTS {table_tmp1};
        DROP TABLE IF EXISTS {table_tmp2};
    """
    cur.execute(SQL(query_1).format(
        table_tmp1=Identifier('simplified_land_00_tmp1'),
        table_tmp2=Identifier('simplified_land_00_tmp2'),
    ))


def main():
    con = connect(database=DATABASE)
    con.set_session(autocommit=True)
    cur = con.cursor()
    import_layers()
    fix_lsib(cur)
    fix_land(cur)
    fix_land_simple(cur)
    cleanup_tmp(cur)
    cur.close()
    con.close()
    logger.info('preprocessing')

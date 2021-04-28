import subprocess
from psycopg2 import connect
from psycopg2.sql import SQL, Identifier, Literal
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

geometries = {
    1: 'Point',
    2: 'LineString',
    3: 'Polygon',
}
query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        fid,
        ST_Transform((ST_Dump(
            ST_CollectionExtract(ST_MakeValid(
                ST_Force2D(ST_SnapToGrid(geom, 0.000000001))
            ), {geom_num})
        )).geom, 4326)::GEOMETRY({geom_str}, 4326) as geom
    FROM {table_in};
"""
query_2 = """
    ALTER TABLE {table_in}
    DROP COLUMN IF EXISTS geom;
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT DISTINCT ON (a.fid)
        a.*,
        b.geom
    FROM {table_in1} as a
    LEFT JOIN {table_in2} as b
    ON a.fid = b.fid;
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(name, file, geometry):
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-lco', 'FID=fid',
        '-lco', 'GEOMETRY_NAME=geom',
        '-lco', 'SPATIAL_INDEX=NONE',
        '-nln', f'{name}_tmp1',
        '-f', 'PostgreSQL', f'PG:dbname={DATABASE}',
        file
    ])
    con = connect(database=DATABASE)
    cur = con.cursor()
    cur.execute(SQL(query_1).format(
        table_in=Identifier(f'{name}_tmp1'),
        geom_num=Literal(geometry),
        geom_str=Literal(geometries[geometry]),
        table_out=Identifier(f'{name}_tmp2'),
    ))
    cur.execute(SQL(query_2).format(
        table_in=Identifier(f'{name}_tmp1'),
    ))
    cur.execute(SQL(query_3).format(
        table_in1=Identifier(f'{name}_tmp1'),
        table_in2=Identifier(f'{name}_tmp2'),
        table_out=Identifier(f'{name}_00'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{name}_tmp1'),
        table_tmp2=Identifier(f'{name}_tmp2'),
    ))
    con.commit()
    cur.close()
    con.close()
    logger.info(name)

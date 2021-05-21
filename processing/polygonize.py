from psycopg2 import connect
from psycopg2.sql import SQL, Identifier
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiLineString, 4326) as geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        (ST_Dump(
            ST_Polygonize(geom))
        ).geom::GEOMETRY(Polygon, 4326) as geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.id,
        a.geom
    FROM {table_in1} as a
    JOIN {table_in2} as b
    ON ST_Within(b.geom, a.geom);
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main():
    con = connect(database=DATABASE)
    cur = con.cursor()
    cur.execute(SQL(query_1).format(
        table_in=Identifier('adm0_lines_00'),
        table_out=Identifier('adm0_lines_01'),
    ))
    cur.execute(SQL(query_2).format(
        table_in=Identifier('adm0_lines_01'),
        table_out=Identifier('adm0_polygons_tmp1'),
    ))
    cur.execute(SQL(query_3).format(
        table_in1=Identifier('adm0_polygons_tmp1'),
        table_in2=Identifier('adm0_points_00'),
        table_out=Identifier('adm0_polygons_00'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier('adm0_polygons_tmp1'),
    ))
    con.commit()
    cur.close()
    con.close()
    logger.info('adm0_polygons')

from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiPolygon, 4326) as geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        ST_Multi(ST_Union(
            ST_CollectionExtract(ST_Difference(a.geom, b.geom), 2)
        ))::GEOMETRY(MultiLineString, 4326) AS geom
    FROM {table_in1} AS a
    CROSS JOIN {table_in2} AS b;
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        (ST_Dump(
            ST_CollectionExtract(ST_Split(a.geom, b.geom), 2)
        )).geom::GEOMETRY(LineString, 4326) AS geom
    FROM {table_in1} AS a
    CROSS JOIN {table_in2} AS b;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(cur):
    # cur.execute(SQL(query_1).format(
    #     table_in=Identifier('lsib_original_00'),
    #     table_out=Identifier('lsib_original_tmp1'),
    # ))
    # cur.execute(SQL(query_2).format(
    #     table_in1=Identifier('lsib_voronoi_00'),
    #     table_in2=Identifier('lsib_original_tmp1'),
    #     table_out=Identifier('lsib_voronoi_tmp1'),
    # ))
    cur.execute(SQL(query_3).format(
        table_in1=Identifier('lsib_voronoi_00'),
        table_in2=Identifier('lsib_original_00'),
        table_out=Identifier('lsib_voronoi_01'),
    ))
    # cur.execute(SQL(drop_tmp).format(
    #     table_tmp1=Identifier('lsib_original_tmp1'),
    #     table_tmp1=Identifier('lsib_voronoi_tmp1'),
    # ))
    logger.info('lsib_lines')

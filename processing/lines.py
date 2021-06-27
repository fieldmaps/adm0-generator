from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        rank,
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiLineString, 4326) as geom
    FROM {table_in}
    GROUP BY rank;
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        a.rank,
        (ST_Dump(ST_CollectionExtract(
            ST_Intersection(a.geom, b.geom)
        , 2))).geom::GEOMETRY(LineString, 4326) AS geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON ST_Intersects(a.geom, b.geom);
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        rank,
        ST_Multi(ST_Union(
            ST_Difference(geom, ST_Boundary(
                ST_MakeEnvelope(-180, -90, 180, 90, 4326)
            ))
        ))::GEOMETRY(MultiLineString, 4326) AS geom
    FROM {table_in}
    GROUP BY rank
    ORDER BY rank;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(cur, name, prefix):
    layer = f'{prefix}{name}'
    cur.execute(SQL(query_1).format(
        table_in=Identifier(f'{layer}_lines_00'),
        table_out=Identifier(f'{layer}_lines_tmp1'),
    ))
    cur.execute(SQL(query_2).format(
        table_in1=Identifier(f'{layer}_lines_tmp1'),
        table_in2=Identifier(f'{layer}_land_01'),
        table_out=Identifier(f'{layer}_lines_tmp2'),
    ))
    cur.execute(SQL(query_3).format(
        table_in=Identifier(f'{layer}_lines_tmp2'),
        table_out=Identifier(f'{layer}_lines_02'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{layer}_lines_tmp1'),
        table_tmp2=Identifier(f'{layer}_lines_tmp2'),
    ))
    logger.info(layer)

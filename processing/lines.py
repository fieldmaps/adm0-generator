from psycopg2.sql import SQL, Identifier, Literal
from .utils import logging, world_views

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        a.fid_1,
        ST_Multi(
            ST_ReducePrecision(
                ST_Union(
                    ST_CollectionExtract(
                        ST_Intersection(a.geom, b.geom)
                    , 2)
                )
            , 0.000000001)
        )::GEOMETRY(MultiLineString, 4326) AS geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON ST_Intersects(a.geom, b.geom)
    GROUP BY fid_1;
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.*,
        {wld} AS wld_view,
        a.geom
    FROM {table_in1} AS a
    LEFT JOIN {table_in2} AS b
    ON a.fid_1 = b.fid_1
    WHERE COALESCE({rank}, rank) > 0;
"""
query_3 = """
    UPDATE {table_out}
    SET rank = COALESCE({rank}, rank);
"""
query_4 = """
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS {rank};
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main(cur, prefix, world):
    cur.execute(SQL(query_1).format(
        table_in1=Identifier(f'{prefix}lines_00'),
        table_in2=Identifier(f'{prefix}land_01'),
        table_out=Identifier(f'{prefix}lines_02_tmp1_{world}'),
    ))
    cur.execute(SQL(query_2).format(
        table_in1=Identifier(f'{prefix}lines_02_tmp1_{world}'),
        table_in2=Identifier(f'{prefix}attributes_lines'),
        rank=Identifier(f'rank_{world}'),
        wld=Literal(world),
        table_out=Identifier(f'{prefix}lines_02_{world}'),
    ))
    cur.execute(SQL(query_3).format(
        rank=Identifier(f'rank_{world}'),
        table_out=Identifier(f'{prefix}lines_02_{world}'),
    ))
    for wld in world_views:
        cur.execute(SQL(query_4).format(
            rank=Identifier(f'rank_{wld}'),
            table_out=Identifier(f'{prefix}lines_02_{world}'),
        ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{prefix}lines_02_tmp1_{world}'),
    ))
    logger.info(f'{prefix}{world}')

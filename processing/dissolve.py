from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        COALESCE ({world_view}::TEXT, id) AS id,
        geom
    FROM {table_in};
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiPolygon, 4326) AS geom
    FROM {table_in}
    GROUP BY id;
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.*,
        a.geom
    FROM {table_in1} AS a
    LEFT JOIN {table_in2} AS b
    ON a.id = b.id
    ORDER BY a.id;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(cur, prefix, world):
    cur.execute(SQL(query_1).format(
        table_in=Identifier(f'{prefix}polygons_01'),
        world_view=Identifier(f'wld_{world}'),
        table_out=Identifier(f'{prefix}polygons_tmp1_{world}'),
    ))
    cur.execute(SQL(query_2).format(
        table_in=Identifier(f'{prefix}polygons_tmp1_{world}'),
        table_out=Identifier(f'{prefix}polygons_tmp2_{world}'),
    ))
    cur.execute(SQL(query_3).format(
        table_in1=Identifier(f'{prefix}polygons_tmp2_{world}'),
        table_in2=Identifier(f'{prefix}attributes_points'),
        table_out=Identifier(f'{prefix}polygons_02_{world}'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{prefix}polygons_tmp1_{world}'),
        table_tmp2=Identifier(f'{prefix}polygons_tmp2_{world}'),
    ))
    logger.info(f'{prefix}{world}')

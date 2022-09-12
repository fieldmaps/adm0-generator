from psycopg.sql import SQL, Identifier, Literal
from processing.utils import logging, world_views

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        ST_ReducePrecision(
            (ST_MaximumInscribedCircle(geom)).center
        , 0.000000001)::GEOMETRY(Point, 4326) AS geom
    FROM {table_in};
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.*,
        a.geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON a.id = b.id;
"""
query_3 = """
    ALTER TABLE {table_out}
    ALTER COLUMN wld_view TYPE VARCHAR;
    UPDATE {table_out}
    SET wld_view = {wld};
"""
query_4 = """
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS {polygon},
    DROP COLUMN IF EXISTS {point};
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main(conn, land, world):
    conn.execute(SQL(query_1).format(
        table_in=Identifier(f'{land}_polygons_01_p_{world}'),
        table_out=Identifier(f'{land}_points_01_tmp1_{world}'),
    ))
    conn.execute(SQL(query_2).format(
        table_in1=Identifier(f'{land}_points_01_tmp1_{world}'),
        table_in2=Identifier(f'{land}_attributes_points'),
        table_out=Identifier(f'{land}_points_01_{world}'),
    ))
    conn.execute(SQL(query_3).format(
        wld=Literal(world),
        table_out=Identifier(f'{land}_points_01_{world}'),
    ))
    for wld in world_views:
        conn.execute(SQL(query_4).format(
            polygon=Identifier(f'a_{wld}'),
            point=Identifier(f'p_{wld}'),
            table_out=Identifier(f'{land}_points_01_{world}'),
        ))
    conn.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{land}_points_01_tmp1_{world}'),
    ))
    logger.info(f'{land}_{world}')

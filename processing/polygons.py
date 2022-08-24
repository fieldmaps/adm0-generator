from psycopg.sql import SQL, Identifier, Literal
from processing.utils import logging, world_views

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        COALESCE({world_view_1}::TEXT, {world_view_2}::TEXT, id) AS id,
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
    ON a.id = b.id;
"""
query_4 = """
    ALTER TABLE {table_out}
    ALTER COLUMN wld_view TYPE VARCHAR;
    UPDATE {table_out}
    SET wld_view = {wld};
"""
query_5 = """
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS {polygon},
    DROP COLUMN IF EXISTS {point};
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(conn, prefix, world):
    for output in ['voronoi', 'polygons']:
        for geom, other in [('p', 'a'), ('a', 'a')]:
            conn.execute(SQL(query_1).format(
                table_in=Identifier(f'{prefix}{output}_00'),
                world_view_1=Identifier(f'{geom}_{world}'),
                world_view_2=Identifier(f'{other}_{world}'),
                table_out=Identifier(
                    f'{prefix}{output}_01_tmp1_{geom}_{world}'),
            ))
            conn.execute(SQL(query_2).format(
                table_in=Identifier(
                    f'{prefix}{output}_01_tmp1_{geom}_{world}'),
                table_out=Identifier(
                    f'{prefix}{output}_01_tmp2_{geom}_{world}'),
            ))
            conn.execute(SQL(query_3).format(
                table_in1=Identifier(
                    f'{prefix}{output}_01_tmp2_{geom}_{world}'),
                table_in2=Identifier(f'{prefix}attributes_points'),
                table_out=Identifier(f'{prefix}{output}_01_{geom}_{world}'),
            ))
            conn.execute(SQL(query_4).format(
                wld=Literal(world),
                table_out=Identifier(f'{prefix}{output}_01_{geom}_{world}'),
            ))
            for wld in world_views:
                conn.execute(SQL(query_5).format(
                    polygon=Identifier(f'a_{wld}'),
                    point=Identifier(f'p_{wld}'),
                    table_out=Identifier(
                        f'{prefix}{output}_01_{geom}_{world}'),
                ))
            conn.execute(SQL(drop_tmp).format(
                table_tmp1=Identifier(
                    f'{prefix}{output}_01_tmp1_{geom}_{world}'),
                table_tmp2=Identifier(
                    f'{prefix}{output}_01_tmp2_{geom}_{world}'),
            ))
            logger.info(f'{prefix}{world}_{output}_{geom}')

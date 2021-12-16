from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        (
            ST_MaximumInscribedCircle(geom)
        ).center::GEOMETRY(Point, 4326) AS geom
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
    ON a.id = b.id
    WHERE b.label IS NOT NULL
    ORDER BY a.id;
"""
query_3 = """
    UPDATE {table_out}
    SET iso_grp = COALESCE (iso_grp, iso3);
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS wld_all
    DROP COLUMN IF EXISTS wld_intl
    DROP COLUMN IF EXISTS wld_usa
    DROP COLUMN IF EXISTS wld_chn
    DROP COLUMN IF EXISTS wld_ind;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main(cur, prefix, world):
    cur.execute(SQL(query_1).format(
        table_in=Identifier(f'{prefix}polygons_02_{world}'),
        table_out=Identifier(f'{prefix}points_tmp1_{world}'),
    ))
    cur.execute(SQL(query_2).format(
        table_in1=Identifier(f'{prefix}points_tmp1_{world}'),
        table_in2=Identifier(f'{prefix}attributes_points'),
        table_out=Identifier(f'{prefix}points_01_{world}'),
    ))
    cur.execute(SQL(query_3).format(
        table_out=Identifier(f'{prefix}points_01_{world}'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{prefix}points_tmp1_{world}'),
    ))
    logger.info(f'{prefix}{world}')

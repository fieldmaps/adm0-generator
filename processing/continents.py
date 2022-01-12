from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT a.*
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON ST_Intersects(a.geom, b.geom)
    AND ST_Crosses(a.geom, b.geom);
    CREATE INDEX ON {table_out} USING GIST(geom);
"""


def main(cur, prefix, _):
    cur.execute(SQL(query_1).format(
        table_in1=Identifier(f'{prefix}land_00'),
        table_in2=Identifier(f'{prefix}lines_01'),
        table_out=Identifier(f'{prefix}land_01'),
    ))
    logger.info(f'{prefix}continents')

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


def main(cur):
    cur.execute(SQL(query_1).format(
        table_in1=Identifier('land_polygons_00'),
        table_in2=Identifier('adm0_lines_01'),
        table_out=Identifier('land_polygons_01'),
    ))
    logger.info('land_polygons')

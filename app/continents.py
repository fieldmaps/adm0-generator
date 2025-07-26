from psycopg.sql import SQL, Identifier

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


def main(conn, land, _):
    conn.execute(
        SQL(query_1).format(
            table_in1=Identifier(f"{land}_land_00"),
            table_in2=Identifier(f"{land}_lines_01"),
            table_out=Identifier(f"{land}_land_01"),
        ),
    )
    logger.info(f"{land}_continents")

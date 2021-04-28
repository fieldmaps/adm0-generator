from psycopg2 import connect
from psycopg2.sql import SQL, Identifier
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        adm0_fid,
        (
            ST_MaximumInscribedCircle(geom)
        ).center::GEOMETRY(Point, 4326) AS geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.*,
        a.geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON a.adm0_fid = b.adm0_fid
    ORDER BY a.adm0_fid;
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main():
    con = connect(database=DATABASE)
    cur = con.cursor()
    cur.execute(SQL(query_1).format(
        table_in=Identifier('adm0_polygons_01'),
        table_out=Identifier('adm0_points_tmp1'),
    ))
    cur.execute(SQL(query_2).format(
        table_in1=Identifier('adm0_points_tmp1'),
        table_in2=Identifier('adm0_attributes'),
        table_out=Identifier('adm0_points_01'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier('adm0_points_tmp1'),
    ))
    con.commit()
    cur.close()
    con.close()
    logger.info('adm0_points')

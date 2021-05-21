from psycopg2 import connect
from psycopg2.sql import SQL, Identifier
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        type,
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiLineString, 4326) as geom
    FROM {table_in}
    GROUP BY id, type;
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        a.id,
        a.type,
        (ST_Dump(ST_CollectionExtract(
            ST_Intersection(a.geom, b.geom), 2
        ))).geom::GEOMETRY(LineString, 4326) AS geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON ST_Intersects(a.geom, b.geom);
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        type,
        ST_Multi(ST_Union(
            ST_Difference(geom, ST_Boundary(
                ST_MakeEnvelope(-180, -90, 180, 90, 4326)
            ))
        ))::GEOMETRY(MultiLineString, 4326) AS geom
    FROM {table_in}
    GROUP BY id, type
    ORDER BY type, id;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main():
    con = connect(database=DATABASE)
    cur = con.cursor()
    cur.execute(SQL(query_1).format(
        table_in=Identifier('adm0_lines_00'),
        table_out=Identifier('adm0_lines_tmp1'),
    ))
    cur.execute(SQL(query_2).format(
        table_in1=Identifier('adm0_lines_tmp1'),
        table_in2=Identifier('land_polygons_01'),
        table_out=Identifier('adm0_lines_tmp2'),
    ))
    cur.execute(SQL(query_3).format(
        table_in=Identifier('adm0_lines_tmp2'),
        table_out=Identifier('adm0_lines_02'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier('adm0_lines_tmp1'),
        table_tmp2=Identifier('adm0_lines_tmp2'),
    ))
    con.commit()
    cur.close()
    con.close()
    logger.info('adm0_lines')

from psycopg.sql import SQL, Identifier

from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.id,
        a.geom
    FROM {table_in1} AS a
    JOIN {table_in3} AS b
    ON ST_Within(a.geom, b.geom)
    UNION ALL
    SELECT
        b.id,
        (ST_Dump(
            ST_CollectionExtract(ST_Intersection(a.geom, b.geom), 3)
        )).geom::GEOMETRY(Polygon, 4326) AS geom
    FROM {table_in2} AS a
    JOIN {table_in3} AS b
    ON ST_Intersects(a.geom, b.geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        id,
        ST_Multi(
            ST_ReducePrecision(
                ST_Union(geom)
            , 0.000000001)
        )::GEOMETRY(MultiPolygon, 4326) as geom
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
    JOIN {table_in2} AS b
    ON a.id = b.id;
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def main(conn, land, _):
    conn.execute(
        SQL(query_1).format(
            table_in1=Identifier(f"{land}_land_00"),
            table_in2=Identifier(f"{land}_land_01"),
            table_in3=Identifier(f"{land}_voronoi_00"),
            table_out=Identifier(f"{land}_polygons_00_tmp1"),
        ),
    )
    conn.execute(
        SQL(query_2).format(
            table_in=Identifier(f"{land}_polygons_00_tmp1"),
            table_out=Identifier(f"{land}_polygons_00_tmp2"),
        ),
    )
    conn.execute(
        SQL(query_3).format(
            table_in1=Identifier(f"{land}_polygons_00_tmp2"),
            table_in2=Identifier(f"{land}_attributes_points"),
            table_out=Identifier(f"{land}_polygons_00"),
        ),
    )
    conn.execute(
        SQL(drop_tmp).format(
            table_tmp1=Identifier(f"{land}_polygons_00_tmp1"),
            table_tmp2=Identifier(f"{land}_polygons_00_tmp2"),
        ),
    )
    logger.info(f"{land}_intersection")

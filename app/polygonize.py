from psycopg.sql import SQL, Identifier

from .utils import logging

logger = logging.getLogger(__name__)

query_1 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        ST_Multi(
            ST_Union(geom)
        )::GEOMETRY(MultiLineString, 4326) as geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_2 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        (ST_Dump(
            ST_Polygonize(geom))
        ).geom::GEOMETRY(Polygon, 4326) as geom
    FROM {table_in};
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_3 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.id,
        a.geom
    FROM {table_in1} as a
    JOIN {table_in2} as b
    ON ST_DWithin(b.geom, a.geom, 0);
    CREATE INDEX ON {table_out} USING GIST(geom);
"""
query_4 = """
    DROP TABLE IF EXISTS {table_out};
    CREATE TABLE {table_out} AS
    SELECT
        b.*,
        a.geom
    FROM {table_in1} AS a
    JOIN {table_in2} AS b
    ON a.id = b.id;
"""
query_5 = """
    SELECT EXISTS(
        SELECT 1
        FROM {table_in} a
        JOIN {table_in} b
        ON ST_Within(a.geom, b.geom)
        WHERE a.id != b.id
    );
"""
query_6 = """
    SELECT ST_NumInteriorRings(ST_Union(geom))
    FROM {table_in};
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
    DROP TABLE IF EXISTS {table_tmp2};
"""


def check_topology(conn, land):
    has_duplicates = conn.execute(
        SQL(query_5).format(
            table_in=Identifier(f"{land}_voronoi_00"),
        )
    ).fetchone()[0]
    has_gaps = (
        conn.execute(
            SQL(query_6).format(
                table_in=Identifier(f"{land}_voronoi_00"),
            )
        ).fetchone()[0]
        > 0
    )
    if has_duplicates or has_gaps:
        overlaps_txt = f"DUPLICATES" if has_duplicates else ""
        and_txt = f" & " if has_gaps and has_duplicates else ""
        gaps_txt = f"GAPS" if has_gaps else ""
        logger.info(f"{overlaps_txt}{and_txt}{gaps_txt}: {land}")
        raise RuntimeError(f"{overlaps_txt}{and_txt}{gaps_txt} in polygons.")


def main(conn, land, _):
    conn.execute(
        SQL(query_1).format(
            table_in=Identifier(f"{land}_lines_00"),
            table_out=Identifier(f"{land}_lines_01"),
        )
    )
    conn.execute(
        SQL(query_2).format(
            table_in=Identifier(f"{land}_lines_01"),
            table_out=Identifier(f"{land}_voronoi_00_tmp1"),
        )
    )
    conn.execute(
        SQL(query_3).format(
            table_in1=Identifier(f"{land}_voronoi_00_tmp1"),
            table_in2=Identifier(f"{land}_points_00"),
            table_out=Identifier(f"{land}_voronoi_00_tmp2"),
        )
    )
    conn.execute(
        SQL(query_4).format(
            table_in1=Identifier(f"{land}_voronoi_00_tmp2"),
            table_in2=Identifier(f"{land}_attributes_points"),
            table_out=Identifier(f"{land}_voronoi_00"),
        )
    )
    conn.execute(
        SQL(drop_tmp).format(
            table_tmp1=Identifier(f"{land}_voronoi_00_tmp1"),
            table_tmp2=Identifier(f"{land}_voronoi_00_tmp2"),
        )
    )
    check_topology(conn, land)
    logger.info(f"{land}_polygonize")

from psycopg2.sql import SQL, Identifier
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
    SELECT EXISTS(
        SELECT 1
        FROM {table_in} a
        JOIN {table_in} b
        ON ST_Within(a.geom, b.geom)
        WHERE a.id != b.id
    );
"""
query_5 = """
    SELECT ST_NumInteriorRings(ST_Union(geom))
    FROM {table_in};
"""
drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def check_topology(cur, prefix):
    cur.execute(SQL(query_4).format(
        table_in=Identifier(f'{prefix}polygons_00'),
    ))
    has_duplicates = cur.fetchone()[0]
    cur.execute(SQL(query_5).format(
        table_in=Identifier(f'{prefix}polygons_00'),
    ))
    has_gaps = cur.fetchone()[0] > 0
    if has_duplicates or has_gaps:
        overlaps_txt = f'DUPLICATES' if has_duplicates else ''
        and_txt = f' & ' if has_gaps and has_duplicates else ''
        gaps_txt = f'GAPS' if has_gaps else ''
        logger.info(f'{overlaps_txt}{and_txt}{gaps_txt}: {prefix}')
        raise RuntimeError(f'{overlaps_txt}{and_txt}{gaps_txt} in polygons.')


def main(cur, prefix, _):
    cur.execute(SQL(query_1).format(
        table_in=Identifier(f'{prefix}lines_00'),
        table_out=Identifier(f'{prefix}lines_01'),
    ))
    cur.execute(SQL(query_2).format(
        table_in=Identifier(f'{prefix}lines_01'),
        table_out=Identifier(f'{prefix}polygons_00_tmp1'),
    ))
    cur.execute(SQL(query_3).format(
        table_in1=Identifier(f'{prefix}polygons_00_tmp1'),
        table_in2=Identifier(f'{prefix}points_00'),
        table_out=Identifier(f'{prefix}polygons_00'),
    ))
    cur.execute(SQL(drop_tmp).format(
        table_tmp1=Identifier(f'{prefix}polygons_00_tmp1'),
    ))
    check_topology(cur, prefix)
    logger.info(f'{prefix}polygonize')

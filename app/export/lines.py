"""Build final output lines table per world view."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import GEOM_PRECISION, world_views

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Clip boundary lines to land and filter by world view."""
    lines_00 = f"{land}_lines_00"
    land_01 = f"{land}_land_01"
    attrs = f"{land}_attributes_lines"
    out = f"{land}_lines_02_{world}"
    tmp = f"{land}_lines_clipped"

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{tmp}" (
            country1 VARCHAR,
            country2 VARCHAR,
            rank BIGINT,
            label VARCHAR,
            geom GEOMETRY
        )
    """)

    fids = [
        r[0] for r in conn.execute(f'SELECT DISTINCT "FID" FROM "{land_01}"').fetchall()
    ]
    for fid in fids:
        land_wkb = conn.execute(
            f'SELECT ST_AsWKB(geom) FROM "{land_01}" WHERE "FID" = $1', [fid]
        ).fetchone()[0]
        conn.execute(
            f"""--sql
            INSERT INTO "{tmp}"
            SELECT country1, country2, rank, label,
                   ST_CollectionExtract(ST_Intersection(a.geom, ST_GeomFromWKB($1)), 2) AS geom
            FROM "{lines_00}" AS a
            WHERE ST_Intersects(a.geom, ST_GeomFromWKB($1))
        """,
            [land_wkb],
        )

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{out}" AS
        WITH clipped AS (
            SELECT
                country1,
                country2,
                rank,
                label,
                ST_Multi(
                    ST_ReducePrecision(ST_Union_Agg(geom), {GEOM_PRECISION})
                ) AS geom
            FROM "{tmp}"
            WHERE NOT ST_IsEmpty(geom)
            GROUP BY country1, country2, rank, label
        )
        SELECT
            b.*,
            '{world}' AS wld_view,
            a.geom
        FROM clipped AS a
        LEFT JOIN "{attrs}" AS b
        ON a.country1 = b.country1
        AND a.country2 = b.country2
        AND a.rank = b.rank
        AND a.label = b.label
        WHERE COALESCE("rank_{world}", a.rank) > 0
    """)

    conn.execute(f'DROP TABLE IF EXISTS "{tmp}"')

    conn.execute(f"""--sql
        UPDATE "{out}"
        SET rank = COALESCE("rank_{world}", rank)
    """)

    for wld in world_views:
        conn.execute(f'ALTER TABLE "{out}" DROP COLUMN IF EXISTS "rank_{wld}"')

    logger.info("%s_%s", land, world)

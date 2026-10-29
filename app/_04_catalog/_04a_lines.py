"""Build final output lines table per world view."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import GEOM_PRECISION, bounds_of, world_views

logger = getLogger(__name__)


def _clip(conn: DuckDBPyConnection, land: str, keys: list[str], tmp: str) -> None:
    """Clip each boundary line to each crossed land mass into ``tmp``."""
    lines_00 = f"{land}_lines_00"
    land_01 = f"{land}_land_01"
    key_list = ", ".join(f'"{k}"' for k in keys)
    params = ", ".join(f"${i}" for i in range(1, len(keys) + 1))
    n = len(keys)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{tmp}" AS
        SELECT {key_list}, geom FROM "{lines_00}" LIMIT 0
    """)

    # Per-pair INSERT: vectorizing ST_Intersection across all lines for a
    # continent-size land polygon balloons GEOS memory (each chunk x thread
    # deserializes the bound polygon WKB). Bbox-prefilter candidates with
    # ST_Envelope (5-point rect) then loop one (line, land) pair per execute,
    # bound as WKB. Same pattern as _03d_intersection.py.
    fids = [
        r[0] for r in conn.execute(f'SELECT DISTINCT "FID" FROM "{land_01}"').fetchall()
    ]
    for fid in fids:
        land_wkb = conn.execute(
            f'SELECT ST_AsWKB(geom) FROM "{land_01}" WHERE "FID" = $1', [fid]
        ).fetchall()[0][0]
        env_wkb = conn.execute(
            f'SELECT ST_AsWKB(ST_Envelope(geom)) FROM "{land_01}" WHERE "FID" = $1',
            [fid],
        ).fetchall()[0][0]
        candidates = conn.execute(
            f"""--sql
            SELECT {key_list}, ST_AsWKB(geom)
            FROM "{lines_00}"
            WHERE ST_Intersects(ST_Envelope(geom), ST_GeomFromWKB($1))
            """,
            [env_wkb],
        ).fetchall()
        for *vals, line_wkb in candidates:
            conn.execute(
                f"""--sql
                INSERT INTO "{tmp}"
                SELECT {params},
                       ST_CollectionExtract(
                           ST_Intersection(
                               ST_GeomFromWKB(${n + 1}),
                               ST_GeomFromWKB(${n + 2})
                           ), 2
                       )
                """,
                [*vals, line_wkb, land_wkb],
            )


def _dissolve_sql(keys: list[str], tmp: str) -> str:
    key_list = ", ".join(f'"{k}"' for k in keys)
    return f"""--sql
        SELECT
            {key_list},
            ST_Multi(
                ST_ReducePrecision(ST_Union_Agg(geom), {GEOM_PRECISION})
            ) AS geom
        FROM "{tmp}"
        WHERE NOT ST_IsEmpty(geom)
        GROUP BY {key_list}
    """


def _gaul(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Clip GAUL lines to land, dropping world-frame closure segments."""
    attrs = f"{land}_attributes_lines"
    out = f"{land}_lines_02_{world}"
    tmp = f"{land}_lines_clipped"
    _clip(conn, land, ["adm_id"], tmp)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{out}" AS
        WITH clipped AS ({_dissolve_sql(["adm_id"], tmp)})
        SELECT b.*, '{world}' AS wld_view, a.geom
        FROM clipped AS a
        JOIN "{attrs}" AS b ON a.adm_id = b.adm_id
        WHERE b.kind != 'frame'
    """)
    conn.execute(f'DROP TABLE IF EXISTS "{tmp}"')


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Clip boundary lines to land and filter by world view."""
    if bounds_of(land) == "gaul":
        _gaul(conn, land, world)
        logger.info("%s_%s", land, world)
        return
    attrs = f"{land}_attributes_lines"
    out = f"{land}_lines_02_{world}"
    tmp = f"{land}_lines_clipped"
    keys = ["country1", "country2", "rank", "label"]
    _clip(conn, land, keys, tmp)

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{out}" AS
        WITH clipped AS ({_dissolve_sql(keys, tmp)})
        SELECT
            b.*,
            '{world}' AS wld_view,
            a.geom
        FROM clipped AS a
        LEFT JOIN "{attrs}" AS b
        ON a.country1 = b.country1
        AND a.country2 = b.country2
        AND a.rank = b.rank
        AND a.label IS NOT DISTINCT FROM b.label
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

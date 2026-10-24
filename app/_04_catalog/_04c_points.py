"""Build final output points table per world view."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import GEOM_PRECISION, world_views

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Compute label points as maximum inscribed circle centers."""
    polygons_in = f"{land}_polygons_01_p_{world}"
    out = f"{land}_points_01_{world}"
    attrs = f"{land}_attributes_points"

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{out}" AS
        WITH centers AS (
            SELECT id,
                   ST_ReducePrecision(
                       ST_MaximumInscribedCircle(geom).center,
                       {GEOM_PRECISION}
                   ) AS geom
            FROM "{polygons_in}"
        )
        SELECT b.* EXCLUDE (wld_view, wld_notes),
               '{world}' AS wld_view, b.wld_notes, a.geom
        FROM centers AS a
        JOIN "{attrs}" AS b ON a.id = b.id
    """)

    for wld in world_views:
        conn.execute(f'ALTER TABLE "{out}" DROP COLUMN IF EXISTS "a_{wld}"')
        conn.execute(f'ALTER TABLE "{out}" DROP COLUMN IF EXISTS "p_{wld}"')

    logger.info("%s_%s", land, world)

"""Build final output polygons table per world view."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import world_views

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Dissolve polygons by world-view IDs and join attributes."""
    attrs = f"{land}_attributes_points"
    for output in ["voronoi", "polygons"]:
        for geom, other in [("p", "a"), ("a", "a")]:
            src = f"{land}_{output}_00"
            out = f"{land}_{output}_01_{geom}_{world}"

            conn.execute(f"""--sql
                CREATE OR REPLACE TABLE "{out}" AS
                WITH renamed AS (
                    SELECT
                        COALESCE(
                            "{geom}_{world}"::TEXT, "{other}_{world}"::TEXT, id
                        ) AS id,
                        geom
                    FROM "{src}"
                ),
                dissolved AS (
                    SELECT id, ST_Multi(ST_Union_Agg(geom)) AS geom
                    FROM renamed
                    GROUP BY id
                )
                SELECT b.* EXCLUDE (wld_view, wld_notes),
                       '{world}' AS wld_view, b.wld_notes, a.geom
                FROM dissolved AS a
                LEFT JOIN "{attrs}" AS b ON a.id = b.id
            """)

            for wld in world_views:
                conn.execute(f'ALTER TABLE "{out}" DROP COLUMN IF EXISTS "a_{wld}"')
                conn.execute(f'ALTER TABLE "{out}" DROP COLUMN IF EXISTS "p_{wld}"')

            logger.info("%s_%s_%s_%s", land, world, output, geom)

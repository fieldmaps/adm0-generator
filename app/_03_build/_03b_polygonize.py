"""Union boundary lines, polygonize, and join resulting polygons to points."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.utils import discard, has_invalid_coverage

logger = getLogger(__name__)


def _check_topology(conn: DuckDBPyConnection, land: str) -> None:
    """Raise if voronoi polygons have invalid edges or missing polygons."""
    table = f"{land}_voronoi_00"
    points = f"{land}_points_00"
    has_invalid_edges = has_invalid_coverage(conn, table)
    voronoi_count, points_count = conn.execute(f"""--sql
        SELECT
            (SELECT COUNT(*) FROM "{table}"),
            (SELECT COUNT(*) FROM "{points}")
    """).fetchall()[0]
    has_missing = voronoi_count != points_count
    if has_invalid_edges or has_missing:
        edges_txt = "INVALID EDGES" if has_invalid_edges else ""
        and_txt = " & " if has_missing and has_invalid_edges else ""
        missing_txt = (
            f"MISSING POLYGONS ({voronoi_count}/{points_count})" if has_missing else ""
        )
        msg = f"{edges_txt}{and_txt}{missing_txt} in polygons."
        logger.info("%s: %s", msg, land)
        raise RuntimeError(msg)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Polygonize boundary lines and assign polygons to nearest point."""
    lines_01 = f"{land}_lines_01"
    voronoi_00 = f"{land}_voronoi_00"
    points_00 = f"{land}_points_00"
    attrs = f"{land}_attributes_points"

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{lines_01}" AS
        SELECT ST_Multi(ST_Union_Agg(geom)) AS geom
        FROM "{land}_lines_00"
    """)

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{voronoi_00}" AS
        WITH polygonized AS (
            SELECT UNNEST(ST_Dump(ST_Polygonize(list(geom)))).geom AS geom
            FROM "{lines_01}"
        ),
        with_id AS (
            SELECT b.id, a.geom
            FROM polygonized AS a
            JOIN "{points_00}" AS b ON ST_DWithin(b.geom, a.geom, 0)
        )
        SELECT b.*, a.geom
        FROM with_id AS a
        JOIN "{attrs}" AS b ON a.id = b.id
    """)

    _check_topology(conn, land)
    discard(conn, points_00)
    logger.info("%s_polygonize", land)

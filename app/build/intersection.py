"""Clip Voronoi polygons to land boundaries."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import GEOM_PRECISION
from app.utils import discard

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Clip voronoi polygons to land and join attributes."""
    land_00 = f"{land}_land_00"
    land_01 = f"{land}_land_01"
    voronoi_00 = f"{land}_voronoi_00"
    polygons_00 = f"{land}_polygons_00"
    attrs = f"{land}_attributes_points"
    tmp1 = f"{land}_polygons_00_tmp1"
    tmp2 = f"{land}_polygons_00_tmp2"

    conn.execute(f'CREATE OR REPLACE TABLE "{tmp1}" (id VARCHAR, geom GEOMETRY)')

    # Boundary land: process one (land, voronoi) pair at a time. Vectorizing
    # ST_Intersection across N candidate voronoi cells balloons GEOS internal
    # working memory (invisible to duckdb_memory) for the 7M-vertex polygon —
    # bound $1 materializes the WKB once but ST_Intersection's internal
    # structures still allocate per-row. One pair per INSERT caps peak GEOS
    # memory at ~400 MB.
    fids = [
        r[0] for r in conn.execute(f'SELECT DISTINCT "FID" FROM "{land_01}"').fetchall()
    ]
    for fid in fids:
        # Bbox-only candidate filter: ST_Envelope is a 5-point rectangle so
        # DuckDB never deserializes the large land polygon for vectorized
        # bbox-vs-bbox tests.
        env_wkb = conn.execute(
            f'SELECT ST_AsWKB(ST_Envelope(geom)) FROM "{land_01}" WHERE "FID" = $1',
            [fid],
        ).fetchall()[0][0]
        candidates = conn.execute(
            f'SELECT id, ST_AsWKB(geom) FROM "{voronoi_00}" '
            f"WHERE ST_Intersects(geom, ST_GeomFromWKB($1))",
            [env_wkb],
        ).fetchall()
        for vid, vgeom_wkb in candidates:
            conn.execute(
                f"""--sql
                INSERT INTO "{tmp1}"
                SELECT $1, ST_CollectionExtract(
                    ST_Intersection(
                        (SELECT geom FROM "{land_01}" WHERE "FID" = $2),
                        ST_GeomFromWKB($3)
                    ), 3
                )
                """,
                [vid, fid, vgeom_wkb],
            )

    # Non-boundary land polygons each fall entirely within one voronoi cell.
    # Materialize representative points first to drop the polygon GEOS buffer
    # before the join. A vectorized join across all 441 voronoi cells x 825K
    # points OOMs even with bbox prefilter (BLOCKWISE_NL_JOIN materializes too
    # much intermediate state at this scale), so loop one voronoi cell at a
    # time with the cell bound as WKB — peak ~100 MB per execute.
    pts_table = f"{land}_land_00_pts"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{pts_table}" AS
        SELECT "FID", ST_PointOnSurface(geom) AS pt
        FROM "{land_00}"
        WHERE "FID" NOT IN (SELECT "FID" FROM "{land_01}")
    """)
    voronoi_cells = conn.execute(
        f'SELECT id, ST_AsWKB(geom) FROM "{voronoi_00}"'
    ).fetchall()
    for vid, vgeom_wkb in voronoi_cells:
        conn.execute(
            f"""--sql
            INSERT INTO "{tmp1}"
            SELECT $1, l.geom
            FROM "{pts_table}" p
            JOIN "{land_00}" l ON l."FID" = p."FID"
            WHERE ST_Contains(ST_GeomFromWKB($2), p.pt)
            """,
            [vid, vgeom_wkb],
        )
    conn.execute(f'DROP TABLE IF EXISTS "{pts_table}"')
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{tmp2}" AS
        SELECT id,
               ST_Multi(ST_ReducePrecision(
                   ST_Union_Agg(geom), {GEOM_PRECISION})) AS geom
        FROM "{tmp1}"
        WHERE NOT ST_IsEmpty(geom)
        GROUP BY id
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{polygons_00}" AS
        SELECT b.*, a.geom
        FROM "{tmp2}" AS a
        JOIN "{attrs}" AS b ON a.id = b.id
    """)
    conn.execute(f'DROP TABLE IF EXISTS "{tmp1}"')
    conn.execute(f'DROP TABLE IF EXISTS "{tmp2}"')
    discard(conn, land_00)
    discard(conn, attrs)
    logger.info("%s_intersection", land)

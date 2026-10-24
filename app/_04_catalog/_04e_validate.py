"""Validate final output tables before export files are cleaned up."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.utils import has_invalid_coverage, raise_issues

logger = getLogger(__name__)


def _check_geometry(conn: DuckDBPyConnection, table: str, issues: list[str]) -> None:
    n = conn.execute(f"""--sql
        SELECT COUNT(*) FROM "{table}"
        WHERE geom IS NULL OR NOT ST_IsValid(geom)
    """).fetchall()[0][0]
    if n:
        issues.append(f"{table}: {n} null/invalid geometries")

    n = conn.execute(f"""--sql
        SELECT COUNT(*) FROM "{table}"
        WHERE geom IS NOT NULL AND (
            ST_XMin(geom) < -180 OR ST_XMax(geom) > 180 OR
            ST_YMin(geom) < -90 OR ST_YMax(geom) > 90
        )
    """).fetchall()[0][0]
    if n:
        issues.append(f"{table}: {n} geometries outside lon/lat bounds")


def _check_id(
    conn: DuckDBPyConnection, table: str, id_col: str, issues: list[str]
) -> None:
    total, distinct, n_null = conn.execute(f"""--sql
        SELECT COUNT(*), COUNT(DISTINCT "{id_col}"),
               COUNT(*) FILTER (WHERE "{id_col}" IS NULL)
        FROM "{table}"
    """).fetchall()[0]
    if n_null:
        issues.append(f"{table}: {n_null} null {id_col}")
    if distinct < total - n_null:
        issues.append(f"{table}: {total - n_null - distinct} duplicate {id_col}")


def _check_attrs_joined(
    conn: DuckDBPyConnection, table: str, issues: list[str]
) -> None:
    """Flag rows where the LEFT JOIN against the attributes table missed."""
    n = conn.execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE wld_land IS NULL'
    ).fetchall()[0][0]
    if n:
        issues.append(f"{table}: {n} rows with no matching attribute row")


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Validate final lines/polygons/points tables for one land and world view."""
    lines = f"{land}_lines_02_{world}"
    polygons = f"{land}_polygons_01_a_{world}"
    polygons_p = f"{land}_polygons_01_p_{world}"
    points = f"{land}_points_01_{world}"

    issues: list[str] = []

    _check_geometry(conn, lines, issues)
    _check_geometry(conn, polygons, issues)
    _check_geometry(conn, points, issues)

    _check_id(conn, lines, "adm_id", issues)
    _check_id(conn, polygons, "adm0_id", issues)
    _check_id(conn, points, "adm0_id", issues)

    _check_attrs_joined(conn, lines, issues)
    _check_attrs_joined(conn, polygons, issues)

    if has_invalid_coverage(conn, polygons):
        issues.append(f"{polygons}: overlaps or gaps between country polygons")

    points_n, polygons_p_n = conn.execute(f"""--sql
        SELECT
            (SELECT COUNT(*) FROM "{points}"),
            (SELECT COUNT(*) FROM "{polygons_p}")
    """).fetchall()[0]
    if points_n != polygons_p_n:
        issues.append(
            f"{points}: {points_n} rows but {polygons_p} has {polygons_p_n} "
            "(join to attributes dropped rows)"
        )

    raise_issues(issues, f"{land}_{world}_validate")
    logger.info("%s_%s", land, world)

"""Write catalog GeoParquet for lines, points, and polygons, plus voronoi."""

from logging import getLogger
from pathlib import Path

from duckdb import DuckDBPyConnection
from geoparquet_io.api.table import read

from app.config import (
    CATALOG_DIR,
    EXPORT_LAYERS,
    PARQUET_OPTS,
    catalog_dir,
    land_of,
    output_dir,
    tmp_dir,
)
from app.utils import raise_issues

logger = getLogger(__name__)


def catalog_parquet(land: str, wld: str, geom: str) -> Path:
    """Return the catalog GeoParquet path for a land, world view, and layer."""
    collection = catalog_dir / CATALOG_DIR[land, wld] / f"adm0-{geom}"
    return collection / f"adm0_{geom}.parquet"


def _copy_parquet(
    conn: DuckDBPyConnection, table: str, file_out: Path, *, has_id: bool
) -> None:
    exclude = "(id, geom)" if has_id else "geom"
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (SELECT * EXCLUDE {exclude}, geom AS geometry FROM "{table}")
        TO '{file_out}' {PARQUET_OPTS}
    """)


def main(conn: DuckDBPyConnection, land: str, wld: str) -> None:
    """Write Hilbert-sorted GeoParquet 2.0 to the catalog, one row group per polygon."""
    issues = []
    for geom, _, layer in EXPORT_LAYERS:
        table = f"{land}_{layer}_{wld}"
        has_id = geom != "lines"
        if geom == "voronoi":
            if wld in ("intl", "gaul"):
                voronoi = (
                    output_dir / f"adm0/{land_of(land)}/{wld}/adm0_voronoi.parquet"
                )
                _copy_parquet(conn, table, voronoi, has_id=has_id)
            continue
        staged = tmp_dir / f"{land}/{wld}/adm0_{geom}.parquet"
        _copy_parquet(conn, table, staged, has_id=has_id)
        file_out = catalog_parquet(land, wld, geom)
        file_out.parent.mkdir(parents=True, exist_ok=True)
        read(str(staged)).sort_hilbert().write(
            file_out,
            compression_level=15,
            row_group_rows=1 if geom == "polygons" else None,
            geoparquet_version="2.0",
            write_strategy="streaming",
            overwrite=True,
        )
        staged.unlink()
        expected = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchall()[0][0]
        actual = conn.execute(
            f"SELECT COUNT(*) FROM read_parquet('{file_out}')"
        ).fetchall()[0][0]
        if actual != expected:
            issues.append(f"{file_out}: wrote {actual} rows, {table} has {expected}")
    raise_issues(issues, f"{land}_{wld}_parquet")
    logger.info("%s_%s", land, wld)

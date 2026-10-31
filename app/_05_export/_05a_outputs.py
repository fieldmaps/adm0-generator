"""Derive GeoPackage, GDB, Parquet, and XLSX from the catalog GeoParquet."""

from logging import getLogger
from pathlib import Path
from shutil import copy2, rmtree

from duckdb import DuckDBPyConnection

from app._04_catalog._04d_parquet import catalog_parquet
from app.config import EXPORT_LAYERS, land_of, output_dir, tmp_dir
from app.utils import raise_issues, zip_path

logger = getLogger(__name__)

_GDAL_GEOM_TYPE = {
    "MultiLineString": "MULTILINESTRING",
    "Point": "POINT",
    "MultiPolygon": "MULTIPOLYGON",
}


def _verify_count(
    conn: DuckDBPyConnection, src: str, file_out: Path, count_sql: str
) -> str | None:
    """Return an issue string if the written file's row count doesn't match."""
    expected = conn.execute(f"SELECT COUNT(*) FROM {src}").fetchall()[0][0]
    actual = conn.execute(count_sql).fetchall()[0][0]
    if actual != expected:
        return f"{file_out.name}: wrote {actual} rows, source has {expected}"
    return None


def _output_gpkg(
    conn: DuckDBPyConnection, src: str, id_col: str, file_out: Path
) -> str | None:
    """Export source to GeoPackage."""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (
            SELECT * EXCLUDE geometry, geometry AS geom FROM {src} ORDER BY {id_col}
        )
        TO '{file_out}' (FORMAT GDAL, DRIVER 'GPKG', SRS 'EPSG:4326')
    """)
    return _verify_count(
        conn, src, file_out, f"SELECT COUNT(*) FROM ST_Read('{file_out}')"
    )


def _output_gdb(
    conn: DuckDBPyConnection, src: str, id_col: str, geom_type: str, gdb: Path
) -> str | None:
    """Export source to OpenFileGDB."""
    gdb.parent.mkdir(parents=True, exist_ok=True)
    rmtree(gdb, ignore_errors=True)
    conn.execute(f"""--sql
        COPY (
            SELECT * EXCLUDE geometry, ST_MakeValid(geometry) AS geom
            FROM {src}
            ORDER BY {id_col}
        )
        TO '{gdb}' (
            FORMAT GDAL,
            DRIVER 'OpenFileGDB',
            GEOMETRY_TYPE '{_GDAL_GEOM_TYPE[geom_type]}',
            SRS 'EPSG:4326'
        )
    """)
    return _verify_count(conn, src, gdb, f"SELECT COUNT(*) FROM ST_Read('{gdb}')")


def _output_xlsx(
    conn: DuckDBPyConnection, src: str, id_col: str, file_out: Path
) -> str | None:
    """Export source attributes to XLSX."""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (SELECT * EXCLUDE geometry FROM {src} ORDER BY {id_col})
        TO '{file_out}' (FORMAT GDAL, DRIVER 'XLSX')
    """)
    return _verify_count(
        conn, src, file_out, f"SELECT COUNT(*) FROM ST_Read('{file_out}')"
    )


def _output_layer(
    conn: DuckDBPyConnection, land: str, wld: str, spec: tuple[str, str, str]
) -> list[str]:
    geom, geom_type, _ = spec
    if geom == "voronoi" and wld not in ("intl", "gaul"):
        return []
    data_dir = tmp_dir / f"{land}/{wld}"
    data_dir.mkdir(exist_ok=True, parents=True)
    out_dir = output_dir / f"adm0/{land_of(land)}/{wld}"
    out_dir.mkdir(exist_ok=True, parents=True)
    file_name = f"adm0_{geom}"
    gpkg = data_dir / f"{file_name}.gpkg"
    gdb = data_dir / f"{file_name}.gdb"
    parquet = out_dir / f"{file_name}.parquet"
    if geom != "voronoi":
        copy2(catalog_parquet(land, wld, geom), parquet)
    src = f"read_parquet('{parquet}')"
    id_col = "adm_id" if geom == "lines" else "adm0_id"

    issues = [_output_gpkg(conn, src, id_col, gpkg)]

    if geom == "voronoi":
        file_zip = out_dir / f"{gpkg.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(gpkg, file_zip)
        return [i for i in issues if i]

    issues.append(_output_gdb(conn, src, id_col, geom_type, gdb))
    issues.append(_output_xlsx(conn, src, id_col, out_dir / f"{file_name}.xlsx"))
    for f in [gpkg, gdb]:
        file_zip = out_dir / f"{f.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(f, file_zip)
    rmtree(gdb, ignore_errors=True)
    return [i for i in issues if i]


def main(conn: DuckDBPyConnection, land: str, wld: str) -> None:
    """Export all output layers for the given land source and world view."""
    issues: list[str] = []
    for spec in EXPORT_LAYERS:
        issues.extend(_output_layer(conn, land, wld, spec))
    if wld != "intl":
        rmtree(tmp_dir / f"{land}/{wld}", ignore_errors=True)
    raise_issues(issues, f"{land}_{wld}_export")
    logger.info("%s_%s", land, wld)

"""Export adm0 polygons, lines, and points to GeoPackage, GDB, Parquet, and XLSX."""

from logging import getLogger
from pathlib import Path
from shutil import rmtree

from duckdb import DuckDBPyConnection

from app.config import EXPORT_LAYERS, PARQUET_OPTS, cwd
from app.utils import zip_path

logger = getLogger(__name__)

_GDAL_GEOM_TYPE = {
    "MultiLineString": "MULTILINESTRING",
    "Point": "POINT",
    "MultiPolygon": "MULTIPOLYGON",
}


def _output_gpkg(
    conn: DuckDBPyConnection,
    table: str,
    id_col: str,
    file_out: Path,
    *,
    has_id: bool,
) -> None:
    """Export table to GeoPackage."""
    exclude = "EXCLUDE id " if has_id else ""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (SELECT * {exclude}FROM "{table}" ORDER BY {id_col})
        TO '{file_out}' (FORMAT GDAL, DRIVER 'GPKG')
    """)


def _output_gdb(
    conn: DuckDBPyConnection,
    table: str,
    id_col: str,
    geom_type: str,
    gdb: Path,
    *,
    has_id: bool,
) -> None:
    """Export table to OpenFileGDB."""
    exclude = "(id, geom)" if has_id else "geom"
    gdb.parent.mkdir(parents=True, exist_ok=True)
    rmtree(gdb, ignore_errors=True)
    conn.execute(f"""--sql
        COPY (
            SELECT * EXCLUDE {exclude},
                   ST_MakeValid(geom) AS geom
            FROM "{table}"
            ORDER BY {id_col}
        )
        TO '{gdb}' (
            FORMAT GDAL,
            DRIVER 'OpenFileGDB',
            GEOMETRY_TYPE '{_GDAL_GEOM_TYPE[geom_type]}'
        )
    """)


def _output_parquet(
    conn: DuckDBPyConnection,
    table: str,
    id_col: str,
    file_out: Path,
    *,
    has_id: bool,
) -> None:
    """Export table to GeoParquet."""
    exclude = "(id, geom)" if has_id else "geom"
    _opts = PARQUET_OPTS.rstrip(")") + ", ROW_GROUP_SIZE 1)"
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (
            SELECT * EXCLUDE {exclude}, geom AS geometry
            FROM "{table}"
            ORDER BY {id_col}
        )
        TO '{file_out}' {_opts}
    """)


def _output_xlsx(
    conn: DuckDBPyConnection,
    table: str,
    id_col: str,
    file_out: Path,
    *,
    has_id: bool,
) -> None:
    """Export table attributes to XLSX."""
    exclude = "(id, geom)" if has_id else "geom"
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (SELECT * EXCLUDE {exclude} FROM "{table}" ORDER BY {id_col})
        TO '{file_out}' (FORMAT GDAL, DRIVER 'XLSX')
    """)


def _output_layer(
    conn: DuckDBPyConnection, land: str, wld: str, spec: tuple[str, str, str]
) -> None:
    geom, geom_type, layer = spec
    if geom in ["clip", "voronoi"] and wld != "intl":
        return
    data_dir = cwd / f"../tmp/{land}/{wld}"
    data_dir.mkdir(exist_ok=True, parents=True)
    output_dir = cwd / f"../outputs/adm0/{land}/{wld}"
    output_dir.mkdir(exist_ok=True, parents=True)
    file_name = f"adm0_{geom}"
    table = f"{land}_{layer}_{wld}"
    gpkg = data_dir / f"{file_name}.gpkg"
    gdb = data_dir / f"{file_name}.gdb"
    parquet = output_dir / f"{file_name}.parquet"
    xlsx = output_dir / f"{file_name}.xlsx"
    rmtree(gdb, ignore_errors=True)
    is_lines = geom == "lines"
    id_col = "adm_id" if is_lines else "adm0_id"
    has_id = not is_lines

    _output_parquet(conn, table, id_col, parquet, has_id=has_id)
    _output_gpkg(conn, table, id_col, gpkg, has_id=has_id)

    if geom in ["clip", "voronoi"]:
        file_zip = output_dir / f"{gpkg.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(gpkg, file_zip)
        return

    _output_gdb(conn, table, id_col, geom_type, gdb, has_id=has_id)
    _output_xlsx(conn, table, id_col, xlsx, has_id=has_id)
    for f in [gpkg, gdb]:
        file_zip = output_dir / f"{f.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(f, file_zip)
    rmtree(gdb, ignore_errors=True)


def main(conn: DuckDBPyConnection, land: str, wld: str) -> None:
    """Export all output layers for the given land source and world view."""
    for geom, _, _layer in EXPORT_LAYERS:
        if geom in ["clip", "voronoi"] and wld != "intl":
            continue
    for spec in EXPORT_LAYERS:
        _output_layer(conn, land, wld, spec)
    if wld != "intl":
        rmtree(cwd / f"../tmp/{land}/{wld}", ignore_errors=True)
    logger.info("%s_%s", land, wld)

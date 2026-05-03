"""Export adm0 polygons, lines, and points to GeoPackage, GDB, Parquet, and XLSX."""

from logging import getLogger
from pathlib import Path
from shutil import rmtree
from subprocess import run

from duckdb import DuckDBPyConnection

from app.config import EXPORT_LAYERS, PARQUET_OPTS, cwd
from app.utils import zip_path

logger = getLogger(__name__)


def _output_gpkg(
    conn: DuckDBPyConnection, table: str, id_col: str, file_out: Path
) -> None:
    """Export table to GeoPackage."""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (SELECT * EXCLUDE id FROM "{table}" ORDER BY {id_col})
        TO '{file_out}' (
            FORMAT GDAL,
            DRIVER 'GPKG',
            LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom'
        )
    """)


def _output_gdb(geom_type: str, gpkg: Path, gdb: Path) -> None:
    """Convert GeoPackage to OpenFileGDB."""
    run(
        [
            "gdal",
            "vector",
            "pipeline",
            "--config",
            "OGR_ORGANIZE_POLYGONS=ONLY_CCW",
            "!",
            "read",
            str(gpkg),
            "!",
            "make-valid",
            "!",
            "set-geom-type",
            "--geometry-type",
            geom_type,
            "!",
            "set-field-type",
            "--src-field-type",
            "Integer64",
            "--dst-field-type",
            "Real",
            "!",
            "set-field-type",
            "--src-field-type",
            "Date",
            "--dst-field-type",
            "DateTime",
            "!",
            "edit",
            "--unset-fid",
            "!",
            "write",
            str(gdb),
            "--of",
            "OpenFileGDB",
            "--output-layer",
            gdb.stem,
            "--overwrite",
        ],
        check=False,
    )


def _output_parquet(
    conn: DuckDBPyConnection, table: str, id_col: str, file_out: Path
) -> None:
    """Export table to GeoParquet."""
    _opts = PARQUET_OPTS.rstrip(")") + ", ROW_GROUP_SIZE 1)"
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"""--sql
        COPY (
            SELECT * EXCLUDE (id, geom), geom AS geometry
            FROM "{table}"
            ORDER BY {id_col}
        )
        TO '{file_out}' {_opts}
    """)


def _output_xlsx(gpkg: Path, output_dir: Path, file_name: str) -> None:
    """Convert GeoPackage to XLSX."""
    xlsx = output_dir / f"{file_name}.xlsx"
    xlsx.unlink(missing_ok=True)
    run(["gdal", "vector", "convert", "-i", str(gpkg), "-o", str(xlsx)], check=False)


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
    rmtree(gdb, ignore_errors=True)
    id_col = "adm_id" if geom == "lines" else "adm0_id"
    _output_gpkg(conn, table, id_col, gpkg)
    if geom in ["clip", "voronoi"]:
        file_zip = output_dir / f"{gpkg.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(gpkg, file_zip)
        return
    _output_gdb(geom_type, gpkg, gdb)
    _output_xlsx(gpkg, output_dir, file_name)
    _output_parquet(conn, table, id_col, parquet)
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

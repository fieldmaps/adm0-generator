"""Export land polygons to GeoPackage, GDB, and Parquet."""

from logging import getLogger
from pathlib import Path
from shutil import rmtree
from subprocess import run

from duckdb import DuckDBPyConnection

from app.config import PARQUET_OPTS, cwd, tmp_dir
from app.utils import copy_from_db, zip_path

logger = getLogger(__name__)


def _output_gpkg(
    conn: DuckDBPyConnection,
    prepare_db: Path,
    land: str,
    file_out: Path,
    has_ogc_fid: bool,
) -> None:
    """Export land polygons to GeoPackage, reading directly from prepare.duckdb."""
    exclude = " EXCLUDE OGC_FID" if has_ogc_fid else ""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"ATTACH '{prepare_db}' AS prepare_src (READ_ONLY)")
    conn.execute(f"""--sql
        COPY (SELECT *{exclude} FROM prepare_src."{land}_land_00")
        TO '{file_out}' (
            FORMAT GDAL,
            DRIVER 'GPKG',
            LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom'
        )
    """)
    conn.execute("DETACH prepare_src")


def _output_gdb(gpkg: Path, gdb: Path) -> None:
    """Convert land GeoPackage to OpenFileGDB."""
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
            "MultiPolygon",
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
    conn: DuckDBPyConnection,
    prepare_db: Path,
    land: str,
    file_out: Path,
    has_ogc_fid: bool,
) -> None:
    """Export land polygons to GeoParquet, reading directly from prepare.duckdb."""
    exclude = " EXCLUDE (OGC_FID, geom)" if has_ogc_fid else " EXCLUDE geom"
    file_out.parent.mkdir(parents=True, exist_ok=True)
    file_out.unlink(missing_ok=True)
    conn.execute(f"ATTACH '{prepare_db}' AS prepare_src (READ_ONLY)")
    conn.execute(f"""--sql
        COPY (
            SELECT *{exclude}, geom AS geometry
            FROM prepare_src."{land}_land_00"
        )
        TO '{file_out}' {PARQUET_OPTS}
    """)
    conn.execute("DETACH prepare_src")


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Export land polygon outputs for the given land source."""
    prepare_db = tmp_dir / "prepare.duckdb"
    build_db = tmp_dir / "build.duckdb"
    for table in [f"{land}_attributes_points", f"{land}_attributes_lines"]:
        copy_from_db(conn, prepare_db, table)
    for table in [
        f"{land}_land_01",
        f"{land}_lines_00",
        f"{land}_polygons_00",
        f"{land}_voronoi_00",
    ]:
        copy_from_db(conn, build_db, table)
    # Check if the current prepare.duckdb still has OGC_FID (from before the preprocessing fix).
    conn.execute(f"ATTACH '{prepare_db}' AS prepare_src (READ_ONLY)")
    cols = [
        r[0] for r in conn.execute(f'DESCRIBE prepare_src."{land}_land_00"').fetchall()
    ]
    conn.execute("DETACH prepare_src")
    has_ogc_fid = "OGC_FID" in cols
    data_dir = cwd / f"../tmp/{land}/land"
    output_dir = cwd / f"../outputs/adm0/{land}/land"
    gpkg = data_dir / "land_polygons.gpkg"
    gdb = data_dir / "land_polygons.gdb"
    parquet = output_dir / "land_polygons.parquet"
    rmtree(gdb, ignore_errors=True)
    _output_gpkg(conn, prepare_db, land, gpkg, has_ogc_fid)
    _output_gdb(gpkg, gdb)
    _output_parquet(conn, prepare_db, land, parquet, has_ogc_fid)
    for f in [gpkg, gdb]:
        file_zip = output_dir / f"{f.name}.zip"
        file_zip.unlink(missing_ok=True)
        zip_path(f, file_zip)
    rmtree(data_dir, ignore_errors=True)
    logger.info("%s_land", land)

import logging
import shutil
import subprocess
from pathlib import Path

from geopandas import read_file

from .utils import DATABASE, cwd, zip_path

logger = logging.getLogger(__name__)


def output_ogr(land: str, output_dir: Path, file_out: Path):
    file_out.parent.mkdir(parents=True, exist_ok=True)
    opts = (
        [
            *["--config", "OGR_ORGANIZE_POLYGONS", "ONLY_CCW"],
            *["-f", "OpenFileGDB"],
            *["-mapFieldType", "Integer64=Real,Date=DateTime"],
        ]
        if file_out.suffix == ".gdb"
        else []
    )
    subprocess.run(
        [
            "ogr2ogr",
            "-makevalid",
            "-overwrite",
            "-unsetFid",
            *["-nln", file_out.stem],
            *["-nlt", "MultiPolygon"],
            *opts,
            file_out,
            *[f"PG:dbname={DATABASE}", f"{land}_land_00"],
        ],
        check=False,
    )
    file_zip = output_dir / f"{file_out.name}.zip"
    file_zip.unlink(missing_ok=True)
    zip_path(file_out, file_zip)


def output_parquet(file_in: Path, file_out: Path):
    file_out.parent.mkdir(parents=True, exist_ok=True)
    read_file(file_in, use_arrow=True).to_parquet(
        file_out,
        compression="zstd",
        write_covering_bbox=True,
        schema_version="1.1.0",
    )


def main(conn, land, _):
    data_dir = cwd / f"../data/{land}/land"
    output_dir = cwd / f"../outputs/adm0/{land}/land"
    gpkg = data_dir / "land_polygons.gpkg"
    gpkg.unlink(missing_ok=True)
    gdb = data_dir / "land_polygons.gdb"
    parquet = output_dir / "land_polygons.parquet"
    parquet.unlink(missing_ok=True)
    shutil.rmtree(gdb, ignore_errors=True)
    output_ogr(land, output_dir, gpkg)
    output_ogr(land, output_dir, gdb)
    output_parquet(gpkg, parquet)
    shutil.rmtree(data_dir, ignore_errors=True)
    logger.info(f"{land}_land")

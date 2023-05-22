import logging
import shutil
import subprocess
from pathlib import Path

from .utils import DATABASE, cwd, zip_path

logger = logging.getLogger(__name__)


def output_ogr(land: str, output_dir: Path, file_out: Path):
    file_out.parent.mkdir(parents=True, exist_ok=True)
    opts = ["-f", "OpenFileGDB"] if file_out.suffix == ".gdb" else []
    subprocess.run(
        [
            "ogr2ogr",
            *["--config", "OGR_ORGANIZE_POLYGONS", "ONLY_CCW"],
            "-unsetFid",
            "-overwrite",
            "-makevalid",
            *["-nln", file_out.stem],
            *opts,
            file_out,
            *[f"PG:dbname={DATABASE}", f"{land}_land_00"],
        ]
    )
    file_zip = output_dir / f"{file_out.name}.zip"
    file_zip.unlink(missing_ok=True)
    zip_path(file_out, file_zip)


def main(conn, land, _):
    data_dir = cwd / f"../data/{land}/land"
    output_dir = cwd / f"../outputs/{land}/land"
    gpkg = data_dir / "land_polygons.gpkg"
    gpkg.unlink(missing_ok=True)
    gdb = data_dir / "land_polygons.gdb"
    shutil.rmtree(gdb, ignore_errors=True)
    output_ogr(land, output_dir, gpkg)
    output_ogr(land, output_dir, gdb)
    gpkg.unlink(missing_ok=True)
    shutil.rmtree(gdb, ignore_errors=True)
    logger.info(f"{land}_land")
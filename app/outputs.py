import logging
import shutil
import subprocess

from geopandas import read_file
from psycopg.sql import SQL, Identifier

from .utils import DATABASE, cwd, zip_path

logger = logging.getLogger(__name__)


layers = [
    ("lines", "MultiLineString", "lines_02"),
    ("points", "Point", "points_01"),
    ("polygons", "MultiPolygon", "polygons_01_a"),
    ("voronoi", "MultiPolygon", "voronoi_01_a"),
    ("clip", "MultiPolygon", "polygons_01_p"),
]

query_1 = """
    ALTER TABLE {table_out}
    DROP COLUMN IF EXISTS id;
"""


def output_ogr(land, layer, wld, geom, geom_type, output_dir, file_out, id):
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
            *opts,
            *["-sql", f"SELECT * FROM {land}_{layer}_{wld} ORDER BY {id};"],
            *["-nln", file_out.stem],
            *["-nlt", geom_type],
            file_out,
            f"PG:dbname={DATABASE}",
        ],
        check=False,
    )
    if geom in ["clip", "voronoi"]:
        return
    file_zip = output_dir / f"{file_out.name}.zip"
    file_zip.unlink(missing_ok=True)
    zip_path(file_out, file_zip)


def output_parquet(file_in, file_out):
    file_out.parent.mkdir(parents=True, exist_ok=True)
    read_file(file_in, use_arrow=True).to_parquet(
        file_out,
        compression="zstd",
        write_covering_bbox=True,
        schema_version="1.1.0",
    )


def output_xlsx(gpkg, output_dir, file_name):
    xlsx = output_dir / f"{file_name}.xlsx"
    xlsx.unlink(missing_ok=True)
    subprocess.run(["ogr2ogr", xlsx, gpkg], check=False)


def outputs(conn, land, wld, geom, geom_type, layer):
    if geom in ["clip", "voronoi"] and wld != "intl":
        return
    data_dir = cwd / f"../data/{land}/{wld}"
    data_dir.mkdir(exist_ok=True, parents=True)
    output_dir = cwd / f"../outputs/adm0/{land}/{wld}"
    output_dir.mkdir(exist_ok=True, parents=True)
    file_name = f"adm0_{geom}"
    gpkg = data_dir / f"{file_name}.gpkg"
    gpkg.unlink(missing_ok=True)
    gdb = data_dir / f"{file_name}.gdb"
    parquet = output_dir / f"{file_name}.parquet"
    shutil.rmtree(gdb, ignore_errors=True)
    conn.execute(SQL(query_1).format(table_out=Identifier(f"{land}_{layer}_{wld}")))
    id = "adm_id" if geom == "lines" else "adm0_id"
    output_ogr(land, layer, wld, geom, geom_type, output_dir, gpkg, id)
    if geom in ["clip", "voronoi"]:
        return
    output_ogr(land, layer, wld, geom, geom_type, output_dir, gdb, id)
    shutil.rmtree(gdb, ignore_errors=True)
    output_xlsx(gpkg, output_dir, file_name)
    output_parquet(gpkg, parquet)


def main(conn, land, wld):
    for geom, geom_type, layer in layers:
        outputs(conn, land, wld, geom, geom_type, layer)
    if wld != "intl":
        shutil.rmtree(cwd / f"../data/{land}/{wld}", ignore_errors=True)
    logger.info(f"{land}_{wld}")

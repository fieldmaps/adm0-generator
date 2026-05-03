"""Export all tables from each stage duckdb to GeoPackage files for inspection."""

import shutil
from pathlib import Path

import duckdb

tmp_dir = Path("tmp")
out_base = tmp_dir / "layers"
if out_base.exists():
    shutil.rmtree(out_base)

for db_path in sorted(tmp_dir.glob("*.duckdb")):
    name = db_path.stem
    out_dir = out_base / name
    out_dir.mkdir(parents=True)

    c = duckdb.connect(str(db_path), read_only=True)
    c.execute("LOAD spatial")

    for (t,) in c.execute("SHOW TABLES").fetchall():
        cols = dict(
            c.execute(
                "SELECT column_name, data_type FROM duckdb_columns()"
                " WHERE table_name = ?",
                [t],
            ).fetchall()
        )
        has_geom = any(dt == "GEOMETRY" for dt in cols.values())
        exclude = [c_ for c_ in ("id", "OGC_FID", "FID") if c_ in cols]
        exclude_sql = f" EXCLUDE ({', '.join(exclude)})" if exclude else ""

        if has_geom:
            c.execute(
                f'COPY (SELECT *{exclude_sql} FROM "{t}")'
                f" TO '{out_dir / t}.gpkg'"
                " (FORMAT GDAL, DRIVER 'GPKG',"
                " LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom')"
            )
        else:
            c.execute(
                f"COPY (SELECT *{exclude_sql} FROM \"{t}\") TO '{out_dir / t}.csv'"
            )
    c.close()

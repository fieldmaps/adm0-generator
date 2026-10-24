"""Build PMTiles with tylertoo and register each collection with portolan."""

import json
import subprocess
from logging import getLogger

import tylertoo
from duckdb import DuckDBPyConnection

from app.config import catalog_dir, geoms, tmp_dir, world_views

from ._04d_parquet import catalog_parquet

logger = getLogger(__name__)


def _portolan(*args: str) -> dict:
    result = subprocess.run(
        ["portolan", "--format", "json", *args],
        cwd=catalog_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    envelope = json.loads(result.stdout)
    if not envelope["success"]:
        msg = f"portolan {args[0]} failed: {envelope['errors']}"
        raise RuntimeError(msg)
    return envelope


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Write PMTiles beside each catalog parquet, then `portolan add` its collection."""
    for wld in world_views:
        for geom in geoms:
            parquet = catalog_parquet(land, wld, geom)
            overview = tmp_dir / f"{land}/{wld}/adm0_{geom}_overview.parquet"
            tylertoo.overview(str(parquet), str(overview))
            tylertoo.export_pmtiles(
                str(overview),
                str(parquet.with_suffix(".pmtiles")),
                layer_name=parquet.stem,
            )
            overview.unlink()
            wld_date = conn.execute(
                f"SELECT max(wld_date) FROM read_parquet('{parquet}')"
            ).fetchall()[0][0]
            _portolan(
                "add",
                str(parquet.parent.relative_to(catalog_dir)),
                "--pmtiles",
                "--datetime",
                wld_date.isoformat(),
            )
            logger.info("%s_%s_%s", land, wld, geom)


def finalize() -> None:
    """Validate the whole catalog against the Portolan spec."""
    _portolan("check", "--data-scope", "local")
    logger.info("check")

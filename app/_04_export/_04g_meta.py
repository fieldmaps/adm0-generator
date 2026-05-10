"""Write dataset metadata to JSON, CSV, and XLSX."""

from datetime import UTC, datetime
from json import dump
from logging import getLogger

import pandas as pd

from app.config import DATA_URL, lands, output_dir, tmp_dir, world_views
from app.utils import get_source_dates

logger = getLogger(__name__)


def _save_date() -> None:
    """Write today's UTC date to the data directory."""
    with (tmp_dir / "date.txt").open("w") as f:
        f.write(datetime.now(tz=UTC).date().isoformat())


def main() -> None:
    """Write metadata JSON, CSV, and XLSX files."""
    tmp_dir.mkdir(exist_ok=True, parents=True)
    output_dir.mkdir(exist_ok=True, parents=True)
    _save_date()
    osm_date, _ = get_source_dates()
    rows = []
    for land in lands:
        for wld in world_views:
            row = {
                "id": f"{land}_{wld}_adm0",
                "grp": land,
                "wld": wld,
                "adm": 0,
                "date": osm_date,
                "a_parquet": f"{DATA_URL}/{land}/{wld}/adm0_polygons.parquet",
                "a_gpkg": f"{DATA_URL}/{land}/{wld}/adm0_polygons.gpkg.zip",
                "a_gdb": f"{DATA_URL}/{land}/{wld}/adm0_polygons.gdb.zip",
                "a_xlsx": f"{DATA_URL}/{land}/{wld}/adm0_polygons.xlsx",
                "l_parquet": f"{DATA_URL}/{land}/{wld}/adm0_lines.parquet",
                "l_gpkg": f"{DATA_URL}/{land}/{wld}/adm0_lines.gpkg.zip",
                "l_gdb": f"{DATA_URL}/{land}/{wld}/adm0_lines.gdb.zip",
                "l_xlsx": f"{DATA_URL}/{land}/{wld}/adm0_lines.xlsx",
                "p_parquet": f"{DATA_URL}/{land}/{wld}/adm0_points.parquet",
                "p_gpkg": f"{DATA_URL}/{land}/{wld}/adm0_points.gpkg.zip",
                "p_gdb": f"{DATA_URL}/{land}/{wld}/adm0_points.gdb.zip",
                "p_xlsx": f"{DATA_URL}/{land}/{wld}/adm0_points.xlsx",
            }
            rows.append(row)
    with (output_dir / "adm0.json").open("w") as f:
        dump(rows, f, separators=(",", ":"))
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.date
    df.to_csv(output_dir / "adm0.csv", index=False)
    df.to_excel(output_dir / "adm0.xlsx", index=False)
    logger.info("meta")

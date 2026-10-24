"""Load CSV attribute tables into DuckDB."""

from logging import getLogger

import pandas as pd
from duckdb import DuckDBPyConnection

from app.config import input_dir
from app.utils import get_source_date

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str) -> None:
    """Load attribute tables for the given land source."""
    land_date = get_source_date(land)
    lsib_date = get_source_date("lsib")
    for geom in ["points", "lines"]:
        file = input_dir / f"adm0_{geom}.csv"
        df = pd.read_csv(file, keep_default_na=False, na_values=["", "#N/A"])
        if geom == "points":
            df["adm0_src"] = df["id"]
            df["adm0_id"] = df["adm0_src"] + "-" + land_date.replace("-", "")
            df["iso_3_grp"] = df["iso_3_grp"].combine_first(df["iso_3"])
            df["region1_cd"] = df["region1_cd"].combine_first(df["status_cd"])
            df["region1_nm"] = df["region1_nm"].combine_first(df["status_nm"])
            df["region2_cd"] = df["region2_cd"].combine_first(df["region1_cd"])
            df["region2_nm"] = df["region2_nm"].combine_first(df["region1_nm"])
            df["region3_cd"] = df["region3_cd"].combine_first(df["region2_cd"])
            df["region3_nm"] = df["region3_nm"].combine_first(df["region2_nm"])
            for col in ["region1_cd", "region2_cd", "region3_cd"]:
                df[col] = df[col].astype("Int64")
        df["wld_date"] = pd.to_datetime(lsib_date).date()
        df["wld_update"] = pd.to_datetime(land_date).date()
        df["wld_land"] = land
        table = f"{land}_attributes_{geom}"
        conn.register("df_temp", df)
        conn.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM df_temp')
        conn.unregister("df_temp")
    logger.info("%s_attributes", land)

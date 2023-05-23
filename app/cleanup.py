import shutil

from psycopg import connect
from psycopg.sql import SQL, Identifier

from .utils import DATABASE, cwd, lands, logging

logger = logging.getLogger(__name__)

layers_world = [
    "lines_02",
    "points_01",
    "polygons_01_a",
    "polygons_01_p",
    "voronoi_01_a",
    "voronoi_01_p",
]

layers = [
    "attributes_lines",
    "attributes_points",
    "lines_00",
    "lines_01",
    "points_00",
    "polygons_00",
    "polygons_01",
    "voronoi_00",
    "land_01",
]

drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""

drop_shp = """
    DROP TABLE IF EXISTS osm_land_00;
    DROP TABLE IF EXISTS usgs_land_00;
    DROP TABLE IF EXISTS lsib_00;
"""


def main(conn, land, world):
    for l in layers_world:
        conn.execute(
            SQL(drop_tmp).format(
                table_tmp1=Identifier(f"{land}_{l}_{world}"),
            )
        )
    logger.info(f"{land}_{world}")


def postprocessing():
    conn = connect(f"dbname={DATABASE}", autocommit=True)
    for land in lands:
        for l in layers:
            conn.execute(
                SQL(drop_tmp).format(
                    table_tmp1=Identifier(f"{land}_{l}"),
                )
            )
    conn.execute(SQL(drop_shp))
    conn.close()
    logger.info(f"postprocessing")

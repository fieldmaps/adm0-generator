from psycopg import connect
from psycopg.sql import SQL, Identifier
from processing.utils import logging, prefixes, DATABASE

logger = logging.getLogger(__name__)

layers_world = [
    'lines_02',
    'points_01',
    'polygons_02_a',
    'polygons_02_p',
]

layers = [
    'attributes_lines',
    'attributes_points',
    'lines_00',
    'lines_01',
    'points_00',
    'polygons_00',
    'polygons_01',
    'land_01',
]

drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""

drop_shp = """
    DROP TABLE IF EXISTS land_00;
    DROP TABLE IF EXISTS simplified_land_00;
    DROP TABLE IF EXISTS lsib_00;
"""


def main(conn, prefix, world):
    for l in layers_world:
        conn.execute(SQL(drop_tmp).format(
            table_tmp1=Identifier(f'{prefix}{l}_{world}'),
        ))
    logger.info(f'{prefix}{world}')


def postprocessing():
    conn = connect(f'dbname={DATABASE}', autocommit=True)
    for prefix in prefixes:
        for l in layers:
            conn.execute(SQL(drop_tmp).format(
                table_tmp1=Identifier(f'{prefix}{l}'),
            ))
    conn.execute(SQL(drop_shp))
    conn.close()
    logger.info(f'postprocessing')

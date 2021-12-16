from psycopg2 import connect
from psycopg2.sql import SQL, Identifier
from .utils import logging, prefixes, DATABASE

logger = logging.getLogger(__name__)

layers_world = [
    'lines_02',
    'points_01',
    'polygons_02',
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


def main(cur, prefix, world):
    for l in layers_world:
        cur.execute(SQL(drop_tmp).format(
            table_tmp1=Identifier(f'{prefix}{l}_{world}'),
        ))
    logger.info(f'{prefix}{world}')


def postprocessing():
    con = connect(database=DATABASE)
    con.set_session(autocommit=True)
    cur = con.cursor()
    for prefix in prefixes:
        for l in layers:
            cur.execute(SQL(drop_tmp).format(
                table_tmp1=Identifier(f'{prefix}{l}'),
            ))
    cur.execute(SQL(drop_shp))
    cur.close()
    con.close()
    logger.info(f'postprocessing')

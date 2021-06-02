from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

layers = [
    'adm0_attributes',
    'adm0_lines_00',
    'adm0_lines_01',
    'adm0_lines_02',
    'adm0_points_00',
    'adm0_points_01',
    'adm0_polygons_00',
    'adm0_polygons_01',
    'land_polygons_00',
    'land_polygons_01',
]

drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main(cur):
    for layer in layers:
        cur.execute(SQL(drop_tmp).format(
            table_tmp1=Identifier(layer),
        ))
    logger.info(f'cleanup')

from psycopg2.sql import SQL, Identifier
from .utils import logging

logger = logging.getLogger(__name__)

layers = [
    'attributes',
    'lines_00',
    'lines_01',
    'lines_02',
    'points_00',
    'points_01',
    'polygons_00',
    'polygons_01',
    'land_01',
]

drop_tmp = """
    DROP TABLE IF EXISTS {table_tmp1};
"""


def main(cur, name, prefix):
    layer = f'{prefix}{name}'
    for l in layers:
        cur.execute(SQL(drop_tmp).format(
            table_tmp1=Identifier(f'{layer}_{l}'),
        ))
    logger.info(layer)

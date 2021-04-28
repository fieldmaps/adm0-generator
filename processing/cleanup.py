from psycopg2 import connect
from psycopg2.sql import SQL, Identifier
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)


def main(layers):
    con = connect(database=DATABASE)
    cur = con.cursor()
    drop_tmp = """
        DROP TABLE IF EXISTS {table_tmp1};
    """
    for layer in layers:
        cur.execute(SQL(drop_tmp).format(
            table_tmp1=Identifier(layer),
        ))
    con.commit()
    cur.close()
    con.close()
    logger.info(f'cleanup')

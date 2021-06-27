from psycopg2 import connect
from psycopg2.sql import SQL
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

drop_tmp = """
    DROP TABLE IF EXISTS land_00;
    DROP TABLE IF EXISTS simplified_land_00;
    DROP TABLE IF EXISTS lsib_00;
"""


def main():
    con = connect(database=DATABASE)
    con.set_session(autocommit=True)
    cur = con.cursor()
    cur.execute(SQL(drop_tmp))
    cur.close()
    con.close()
    logger.info(f'postprocessing')

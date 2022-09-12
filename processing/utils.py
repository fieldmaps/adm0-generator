import logging
from pathlib import Path
from psycopg import connect

DATABASE = 'adm0_generator'
DATA_URL = 'https://data.fieldmaps.io/adm0'
LAND_URL = 'https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip'
LSIB_URL = 'https://data.geonode.state.gov/LSIB.zip'
LSIB_DATE = '2022-08-22'

lands = ['osm', 'usgs']
world_views = ['intl', 'all', 'usa']
geoms = ['polygons', 'lines', 'points']

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def apply_funcs(prefix, world, *args):
    conn = connect(f'dbname={DATABASE}', autocommit=True)
    for func in args:
        func(conn, prefix, world)
    conn.close()


def get_land_date():
    cwd = Path(__file__).parent
    with open(cwd / '../data/date.txt') as f:
        return f.readline()

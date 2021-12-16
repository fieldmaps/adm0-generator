import logging
from psycopg2 import connect

DATABASE = 'adm0_generator'
DATA_URL = 'https://data.fieldmaps.io/adm0'
LAND_URL = 'https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip'
SIMPLE_LAND_URL = 'https://osmdata.openstreetmap.de/download/simplified-land-polygons-complete-3857.zip'
LSIB_URL = 'https://geonode.state.gov/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typename=geonode%3ALSIB&outputFormat=SHAPE-ZIP&srs=EPSG%3A4326&format_options=charset%3AUTF-8'

prefixes = ['', 'simplified_']
world_views = ['all', 'intl', 'usa', 'chn', 'ind']
geoms = ['lines', 'points', 'polygons']

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def apply_funcs(prefix, world, *args):
    con = connect(database=DATABASE)
    con.set_session(autocommit=True)
    cur = con.cursor()
    for func in args:
        func(cur, prefix, world)
    cur.close()
    con.close()

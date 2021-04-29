import logging

DATABASE = 'adm0_template'
LAND_POLYGONS_URL = 'https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def apply_funcs(name, file, layer, *args):
    for func in args:
        func(name, file, layer)

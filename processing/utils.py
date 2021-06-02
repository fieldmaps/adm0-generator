import logging

DATABASE = 'adm0_template'
LAND_URL = 'https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip'
ADM0_URL = 'https://data.fieldmaps.io/adm0-template'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

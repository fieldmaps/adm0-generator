import json
import pandas as pd
from pathlib import Path
from .utils import (DATA_URL, logging, prefixes,
                    world_views, geoms, get_land_date)

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent
outputs = cwd / '../outputs'


def main():
    outputs.mkdir(exist_ok=True, parents=True)
    data = []
    for prefix in prefixes:
        for wld in world_views:
            for geom in geoms:
                row = {
                    'id': f'{prefix}{wld}_adm0_{geom}',
                    'grp': 'original' if prefix == '' else 'simplified',
                    'wld': wld,
                    'adm': 0,
                    'geom': geom,
                    'date': get_land_date(),
                    'url_gpkg': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_{geom}.gpkg.zip',
                    'url_shp': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_{geom}.shp.zip',
                    'url_xlsx': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_{geom}.xlsx',
                }
                data.append(row)
        data.append({
            'id': f'{prefix}land_polygons',
            'grp': 'original' if prefix == '' else 'simplified',
            'wld': 'land',
            'adm': 0,
            'geom': 'polygons',
            'date': get_land_date(),
            'url_gpkg': f'{DATA_URL}/adm0/land/{prefix}land_polygons.gpkg.zip',
            'url_shp': f'{DATA_URL}/adm0/land/{prefix}land_polygons.shp.zip',
            'url_xlsx': None,
        })
    with open((outputs / f'adm0.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.date
    df.to_csv(outputs / f'adm0.csv', index=False)
    df.to_excel(outputs / f'adm0.xlsx', index=False)
    logger.info('meta')

import json
import pandas as pd
from pathlib import Path
from .utils import DATA_URL, logging, world_views, geoms, get_land_date

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent
outputs = cwd / '../outputs'


def main():
    outputs.mkdir(exist_ok=True, parents=True)
    data = []
    for wld in world_views:
        for geom in geoms:
            row = {
                'id': f'{wld}_{geom}',
                'wld': wld,
                'geom': geom,
                'date': get_land_date(),
                'url_gpkg': f'{DATA_URL}/adm0/{wld}/adm0_{geom}.gpkg.zip',
                'url_shp': f'{DATA_URL}/adm0/{wld}/adm0_{geom}.shp.zip',
                'url_xlsx': f'{DATA_URL}/adm0/{wld}/adm0_{geom}.xlsx',
                'simplified_gpkg': f'{DATA_URL}/adm0/{wld}/simplified_adm0_{geom}.gpkg.zip',
                'simplified_shp': f'{DATA_URL}/adm0/{wld}/simplified_adm0_{geom}.shp.zip',
                'simplified_xlsx': f'{DATA_URL}/adm0/{wld}/simplified_adm0_{geom}.xlsx',
            }
            data.append(row)
    data.append({
        'id': f'land_polygons',
        'wld': 'land',
        'geom': 'polygons',
        'date': get_land_date(),
        'url_gpkg': f'{DATA_URL}/adm0/land/land_polygons.gpkg.zip',
        'url_shp': f'{DATA_URL}/adm0/land/land_polygons.shp.zip',
        'url_xlsx': None,
        'simplified_gpkg': f'{DATA_URL}/adm0/land/simplified_land_polygons.gpkg.zip',
        'simplified_shp': f'{DATA_URL}/adm0/land/simplified_land_polygons.shp.zip',
        'simplified_xlsx': None,
    })
    with open((outputs / f'adm0.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.date
    df.to_csv(outputs / f'adm0.csv', index=False)
    df.to_excel(outputs / f'adm0.xlsx', index=False)
    logger.info('meta')

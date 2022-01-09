import json
import pandas as pd
from pathlib import Path
from .utils import DATA_URL, logging, prefixes, world_views, get_land_date

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent
outputs = cwd / '../outputs'


def main():
    outputs.mkdir(exist_ok=True, parents=True)
    data = []
    for prefix in prefixes:
        for wld in world_views:
            row = {
                'id': f'{prefix}{wld}_adm0',
                'grp': 'original' if prefix == '' else 'simplified',
                'wld': wld,
                'adm': 0,
                'date': get_land_date(),
                'a_gpkg': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_polygons.gpkg.zip',
                'a_shp': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_polygons.shp.zip',
                'a_xlsx': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_polygons.xlsx',
                'l_gpkg': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_lines.gpkg.zip',
                'l_shp': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_lines.shp.zip',
                'l_xlsx': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_lines.xlsx',
                'p_gpkg': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_points.gpkg.zip',
                'p_shp': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_points.shp.zip',
                'p_xlsx': f'{DATA_URL}/adm0/{wld}/{prefix}adm0_points.xlsx',
            }
            data.append(row)
        data.append({
            'id': f'{prefix}land_polygons',
            'grp': 'original' if prefix == '' else 'simplified',
            'wld': 'land',
            'adm': 0,
            'date': get_land_date(),
            'a_gpkg': f'{DATA_URL}/adm0/land/{prefix}land_polygons.gpkg.zip',
            'a_shp': f'{DATA_URL}/adm0/land/{prefix}land_polygons.shp.zip',
            'a_xlsx': None,
            'l_gpkg': None,
            'l_shp': None,
            'p_xlsx': None,
            'p_gpkg': None,
            'p_shp': None,
        })
    with open((outputs / f'adm0.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.date
    df.to_csv(outputs / f'adm0.csv', index=False)
    df.to_excel(outputs / f'adm0.xlsx', index=False)
    logger.info('meta')

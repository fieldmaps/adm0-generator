import json
import pandas as pd
from datetime import date
from pathlib import Path
from processing.utils import DATA_URL, logging, lands, world_views, get_land_date

logger = logging.getLogger(__name__)
cwd = Path(__file__).parent
data = cwd / '../data'
outputs = cwd / '../outputs'


def save_date():
    with open(data / 'date.txt', 'w') as f:
        f.write(date.today().isoformat())


def main():
    data.mkdir(exist_ok=True, parents=True)
    outputs.mkdir(exist_ok=True, parents=True)
    save_date()
    rows = []
    for land in lands:
        for wld in world_views:
            row = {
                'id': f'{land}_{wld}_adm0',
                'grp': land,
                'wld': wld,
                'adm': 0,
                'date': get_land_date(),
                'a_gpkg': f'{DATA_URL}/{land}/{wld}/adm0_polygons.gpkg.zip',
                'a_shp': f'{DATA_URL}/{land}/{wld}/adm0_polygons.shp.zip',
                'a_xlsx': f'{DATA_URL}/{land}/{wld}/adm0_polygons.xlsx',
                'l_gpkg': f'{DATA_URL}/{land}/{wld}/adm0_lines.gpkg.zip',
                'l_shp': f'{DATA_URL}/{land}/{wld}/adm0_lines.shp.zip',
                'l_xlsx': f'{DATA_URL}/{land}/{wld}/adm0_lines.xlsx',
                'p_gpkg': f'{DATA_URL}/{land}/{wld}/adm0_points.gpkg.zip',
                'p_shp': f'{DATA_URL}/{land}/{wld}/adm0_points.shp.zip',
                'p_xlsx': f'{DATA_URL}/{land}/{wld}/adm0_points.xlsx',
            }
            rows.append(row)
        rows.append({
            'id': f'{land}_land_polygons',
            'grp': land,
            'wld': 'land',
            'adm': 0,
            'date': get_land_date(),
            'a_gpkg': f'{DATA_URL}/{land}/land/land_polygons.gpkg.zip',
            'a_shp': f'{DATA_URL}/{land}/land/land_polygons.shp.zip',
            'a_xlsx': None,
            'l_gpkg': None,
            'l_shp': None,
            'p_xlsx': None,
            'p_gpkg': None,
            'p_shp': None,
        })
    with open((outputs / f'adm0.json'), 'w') as f:
        json.dump(rows, f, separators=(',', ':'))
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.date
    df.to_csv(outputs / f'adm0.csv', index=False)
    df.to_excel(outputs / f'adm0.xlsx', index=False)
    logger.info('meta')

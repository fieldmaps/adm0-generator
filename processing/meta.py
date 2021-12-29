import json
from pathlib import Path
from .utils import DATA_URL, prefixes, world_views, geoms, get_land_date

cwd = Path(__file__).parent
outputs = (cwd / '../outputs')


def main():
    outputs.mkdir(exist_ok=True, parents=True)
    data = []
    for world in world_views:
        row = {
            'id': world,
            'date': get_land_date(),
        }
        for prefix in prefixes:
            for geom in geoms:
                row[f'{prefix}{geom}'] = {
                    'gpkg': f'{DATA_URL}/{world}/{prefix}adm0_{geom}.gpkg.zip',
                }
        data.append(row)
    for land in ['land']:
        row = {
            'id': land,
            'date': get_land_date(),
        }
        for prefix in prefixes:
            row[f'{prefix}polygons'] = {
                'gpkg': f'{DATA_URL}/land/{prefix}land_polygons.gpkg.zip',
            }
        data.append(row)
    with open((outputs / 'adm0.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))

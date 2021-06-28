import json
from datetime import date
from pathlib import Path
from .utils import DATA_URL, names, prefixes, geoms

cwd = Path(__file__).parent
outputs = (cwd / '../outputs')


def main():
    outputs.mkdir(exist_ok=True, parents=True)
    data = []
    for name in names:
        row = {
            'id': name,
            'date': date.today().strftime('%Y-%m-%d'),
        }
        for prefix in prefixes:
            for geom in geoms:
                row[f'{prefix}{geom}'] = {
                    'gpkg': f'{DATA_URL}/{name}/{prefix}adm0_{geom}.gpkg.zip',
                }
        data.append(row)
    with open((outputs / 'adm0.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))

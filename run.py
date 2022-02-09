import subprocess
from pathlib import Path

cwd = Path(__file__).parent
land = cwd / 'inputs/land'

layers = ['land_polygons', 'simplified_land_polygons']
exts = ['cpg', 'dbf', 'prj', 'shp', 'shx']

if __name__ == '__main__':
    for layer in layers:
        for ext in exts:
            (land / f'{layer}.{ext}').unlink(missing_ok=True)
    subprocess.run(['python3', '-m', 'processing'])
    subprocess.run(['python3', 'sync.py'])

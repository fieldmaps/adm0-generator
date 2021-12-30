from pathlib import Path
import subprocess

cwd = Path(__file__).parent

if __name__ == '__main__':
    subprocess.run([
        'aws', 's3', 'cp',
        cwd / 'outputs/adm0.json',
        's3://data.fieldmaps.io/adm0.json',
    ])
    subprocess.run([
        'aws', 's3', 'sync',
        '--delete',
        '--exclude', '.*',
        '--exclude', '*.json',
        '--exclude', '*clip.gpkg.zip',
        cwd / f'outputs',
        f's3://data.fieldmaps.io/adm0',
    ])

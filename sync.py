from pathlib import Path
import subprocess

cwd = Path(__file__).parent
world_views = ['land', 'intl', 'all', 'usa', 'chn', 'ind']

if __name__ == '__main__':
    subprocess.run([
        's3cmd', 'sync',
        '--acl-public',
        cwd / 'outputs/adm0.json',
        's3://data.fieldmaps.io/adm0.json',
    ])
    for wld in world_views:
        subprocess.run([
            's3cmd', 'sync',
            '--acl-public',
            '--delete-removed',
            '--rexclude', '\/\.',
            '--multipart-chunk-size-mb=5120',
            cwd / f'outputs/{wld}',
            's3://data.fieldmaps.io/adm0/',
        ])

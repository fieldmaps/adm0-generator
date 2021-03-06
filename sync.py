from pathlib import Path
import subprocess

cwd = Path(__file__).parent
world_views = ['intl', 'all', 'usa', 'chn', 'ind', 'land']
exts = ['json', 'csv', 'xlsx']

if __name__ == '__main__':
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
    for ext in exts:
        subprocess.run([
            's3cmd', 'sync',
            '--acl-public',
            cwd / f'outputs/adm0.{ext}',
            f's3://data.fieldmaps.io/adm0.{ext}',
        ])

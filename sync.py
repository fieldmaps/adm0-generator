from pathlib import Path
import subprocess

cwd = Path(__file__).parent
lands = ['osm', 'usgs']
world_views = ['intl', 'all', 'usa', 'land']
exts = ['json', 'csv', 'xlsx']

if __name__ == '__main__':
    for ext in exts:
        subprocess.run([
            's3cmd', 'sync',
            '--acl-public',
            cwd / f'outputs/adm0.{ext}',
            f's3://data.fieldmaps.io/adm0.{ext}',
        ])
    for land in lands:
        for wld in world_views:
            subprocess.run([
                's3cmd', 'sync',
                '--acl-public',
                '--delete-removed',
                '--rexclude', '\/\.',
                '--multipart-chunk-size-mb=5120',
                cwd / f'outputs/{land}/{wld}',
                f's3://data.fieldmaps.io/adm0/{land}/',
            ])

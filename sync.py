from pathlib import Path
import subprocess

cwd = Path(__file__).parent

layers = ['open']

if __name__ == '__main__':
    subprocess.run([
        's3cmd', 'sync',
        '--acl-public',
        '--delete-removed',
        '--rexclude', '\/\.',
        (cwd / f'outputs/adm0.json').resolve(),
        f's3://fieldmapsdata/adm0.json',
    ])
    for layer in layers:
        subprocess.run([
            's3cmd', 'sync',
            '--acl-public',
            '--delete-removed',
            '--rexclude', '^\.',
            f"{(cwd / f'inputs/{layer}').resolve()}/",
            f's3://fieldmapsdata/adm0-template/{layer}/',
        ])
    for layer in layers:
        subprocess.run([
            's3cmd', 'sync',
            '--acl-public',
            '--delete-removed',
            '--rexclude', '^\.',
            f"{(cwd / f'outputs/{layer}').resolve()}/",
            f's3://fieldmapsdata/adm0/{layer}/',
        ])

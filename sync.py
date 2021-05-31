from pathlib import Path
import subprocess

cwd = Path(__file__).parent

if __name__ == '__main__':
    subprocess.run([
        's3cmd', 'sync',
        '--acl-public',
        '--delete-removed',
        '--rexclude', '^\.',
        f"{(cwd / f'inputs/adm0').resolve()}/",
        f's3://fieldmapsdata/adm0-template/',
    ])

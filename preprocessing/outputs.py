import subprocess
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)


def main(name, input, output):
    output.unlink(missing_ok=True)
    subprocess.run([
        'ogr2ogr',
        '-overwrite',
        '-makevalid',
        '-nln', name,
        output,
        f'PG:dbname={DATABASE}', input,
    ])
    logger.info(name)

from pathlib import Path
import pandas as pd
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = cwd / '../inputs/lsib_extension'


def main(_, prefix, __):
    for geom in ['points', 'lines']:
        file = (input_dir / f'adm0_{geom}.xlsx')
        df = pd.read_excel(file, engine='openpyxl')
        df.to_sql(f'{prefix}attributes_{geom}', con=f'postgresql:///{DATABASE}',
                  if_exists='replace', index=False, method='multi')
    logger.info(prefix)

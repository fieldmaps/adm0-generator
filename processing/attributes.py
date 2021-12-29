from pathlib import Path
import pandas as pd
from .utils import logging, DATABASE, LSIB_DATE, get_land_date

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = cwd / '../inputs/lsib_extension'


def main(_, prefix, __):
    for geom in ['points', 'lines']:
        file = (input_dir / f'adm0_{geom}.xlsx')
        df = pd.read_excel(file, engine='openpyxl',
                           keep_default_na=False, na_values=['', '#N/A'])
        df['date_lsib'] = pd.to_datetime(LSIB_DATE)
        df['date_lsib'] = df['date_lsib'].dt.date
        df['date_land'] = pd.to_datetime(get_land_date())
        df['date_land'] = df['date_land'].dt.date
        df.to_sql(f'{prefix}attributes_{geom}', con=f'postgresql:///{DATABASE}',
                  if_exists='replace', index=False, method='multi')
    logger.info(prefix)

from pathlib import Path
from psycopg2.sql import SQL, Identifier
import pandas as pd
from .utils import logging, DATABASE, LSIB_DATE, get_land_date

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = cwd / '../inputs/lsib_extension'

query_1 = """
    ALTER TABLE {table_out}
    ALTER COLUMN region3_cd TYPE INT8,
    ALTER COLUMN region2_cd TYPE INT8,
    ALTER COLUMN region1_cd TYPE INT8;
"""


def main(cur, prefix, __):
    for geom in ['points', 'lines']:
        file = input_dir / f'adm0_{geom}.csv'
        df = pd.read_csv(file, keep_default_na=False, na_values=['', '#N/A'])
        if geom == 'points':
            df['adm0_src'] = df['id']
            df['adm0_id'] = df['adm0_src'] + '-' + \
                get_land_date().replace('-', '')
            df['iso_3_grp'] = df[f'iso_3_grp'].combine_first(df['iso_3'])
            df['region1_cd'] = df[f'region1_cd'].combine_first(df['status_cd'])
            df['region1_nm'] = df[f'region1_nm'].combine_first(df['status_nm'])
            df['region2_cd'] = df[f'region2_cd'].combine_first(
                df['region1_cd'])
            df['region2_nm'] = df[f'region2_nm'].combine_first(
                df['region1_nm'])
            df['region3_cd'] = df[f'region3_cd'].combine_first(
                df['region2_cd'])
            df['region3_nm'] = df[f'region3_nm'].combine_first(
                df['region2_nm'])
        df['wld_date'] = pd.to_datetime(LSIB_DATE)
        df['wld_date'] = df['wld_date'].dt.date
        df['wld_update'] = pd.to_datetime(get_land_date())
        df['wld_update'] = df['wld_update'].dt.date
        df.to_sql(f'{prefix}attributes_{geom}', con=f'postgresql:///{DATABASE}',
                  if_exists='replace', index=False, method='multi')
        if geom == 'points':
            cur.execute(SQL(query_1).format(
                table_out=Identifier(f'{prefix}attributes_{geom}'),
            ))
    logger.info(f'{prefix}attributes')

import pandas as pd
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)


def main(file):
    df = pd.read_excel(file, engine='openpyxl')
    df.to_sql(f'adm0_attributes', con=f'postgresql:///{DATABASE}',
              if_exists='replace', index=False, method='multi')
    logger.info('attributes')

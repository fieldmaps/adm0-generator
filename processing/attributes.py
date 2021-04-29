import pandas as pd
from sqlalchemy import create_engine
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)
engine_string = f'postgresql:///{DATABASE}'


def main(file):
    engine = create_engine(engine_string)
    df = pd.read_excel(file, engine='openpyxl')
    df.to_sql(f'adm0_attributes', con=engine,
              if_exists='replace', index=False, method='multi')
    logger.info('attributes')

from pathlib import Path
import pandas as pd
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs').resolve()


def main(_, name, prefix):
    layer = f'{prefix}{name}'
    file = (input_dir / f'{name}/adm0_attributes.xlsx')
    df = pd.read_excel(file, engine='openpyxl')
    df.to_sql(f'{layer}_attributes', con=f'postgresql:///{DATABASE}',
              if_exists='replace', index=False, method='multi')
    logger.info(layer)

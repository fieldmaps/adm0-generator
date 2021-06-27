from pathlib import Path
from multiprocessing import Pool
from psycopg2 import connect
from . import (inputs, difference, outputs, cleanup)
from .utils import logging, DATABASE

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_dir = (cwd / '../inputs').resolve()
output_dir = (cwd / '../outputs').resolve()
(input_dir / 'open_tmp').mkdir(exist_ok=True, parents=True)
output_dir.mkdir(exist_ok=True, parents=True)


def import_inputs():
    layers = [
        ('lsib_original', 'open_tmp/lsib_10_lines_dissolved.gpkg'),
        ('lsib_voronoi', 'open_tmp/lsib_annex_dissolved.gpkg'),
    ]
    results = []
    pool = Pool()
    for name, layer in layers:
        args = [name, input_dir / layer]
        result = pool.apply_async(inputs.main, args=args)
        results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


def export_outputs():
    layers = [
        ('adm0_polygons', '01'),
        ('adm0_lines', '02'),
        ('adm0_points', '01'),
    ]
    results = []
    pool = Pool()
    for name, layer in layers:
        args = [name, f'{name}_{layer}', output_dir / f'{name}.gpkg']
        result = pool.apply_async(outputs.main, args=args)
        results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


if __name__ == '__main__':
    logger.info('starting')
    import_inputs()
    con = connect(database=DATABASE)
    con.set_session(autocommit=True)
    cur = con.cursor()
    difference.main(cur)
    cur.close()
    con.close()

from multiprocessing import Pool
from . import (download, preprocessing, inputs, attributes, polygons, land,
               intersection, points, lines, outputs, cleanup, postprocessing)
from .utils import logging, apply_funcs

logger = logging.getLogger(__name__)

funcs = [attributes.main, inputs.main, polygons.main, land.main,
         intersection.main, points.main, lines.main, outputs.main, cleanup.main]

if __name__ == '__main__':
    logger.info('starting')
    download.main()
    preprocessing.main()
    results = []
    pool = Pool()
    for name in ['open', 'humanitarian']:
        for prefix in ['', 'simplified_']:
            args = [name, prefix, *funcs]
            result = pool.apply_async(apply_funcs, args=args)
            results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()
    postprocessing.main()

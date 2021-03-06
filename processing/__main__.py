from multiprocessing import Pool
from . import (download, preprocessing, inputs, attributes, polygonize,
               continents, intersection, land, polygons, points, lines,
               outputs, cleanup, meta)
from .utils import logging, prefixes, world_views, apply_funcs

logger = logging.getLogger(__name__)

funcs_1 = [attributes.main, inputs.main, polygonize.main,
           continents.main, intersection.main]
funcs_2 = [polygons.main, points.main, lines.main, outputs.main, cleanup.main]


def run_pool(world_views, funcs, export_land):
    results = []
    pool = Pool()
    for prefix in prefixes:
        for world in world_views:
            args = [prefix, world, *funcs]
            result = pool.apply_async(apply_funcs, args=args)
            results.append(result)
        if export_land is True:
            result = pool.apply_async(land.main, args=[prefix])
            results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


if __name__ == '__main__':
    logger.info('starting')
    download.main()
    meta.main()
    preprocessing.main()
    run_pool([None], funcs_1, True)
    run_pool(world_views, funcs_2, False)
    cleanup.postprocessing()

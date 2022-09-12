from multiprocessing import Pool
from processing import (download, inputs, attributes, outputs_land, polygonize,
                        continents, intersection, polygons, points, lines,
                        outputs, cleanup, preprocessing, meta)
from processing.utils import logging, lands, apply_funcs, world_views

logger = logging.getLogger(__name__)

funcs_1 = [attributes.main, inputs.main, polygonize.main,
           continents.main, intersection.main]
funcs_2 = [polygons.main, points.main, lines.main, outputs.main, cleanup.main]


def run_pool(world_views, funcs, export_land):
    results = []
    pool = Pool()
    for land in lands:
        for world in world_views:
            args = [land, world, *funcs]
            result = pool.apply_async(apply_funcs, args=args)
            results.append(result)
        if export_land is True:
            result = pool.apply_async(outputs_land.main, args=[land])
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

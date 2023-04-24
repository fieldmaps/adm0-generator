from multiprocessing import Pool

from . import (
    attributes,
    cleanup,
    continents,
    download,
    inputs,
    intersection,
    lines,
    meta,
    outputs,
    outputs_land,
    points,
    polygonize,
    polygons,
    preprocessing,
)
from .utils import apply_funcs, lands, logging, world_views

logger = logging.getLogger(__name__)

funcs_1 = [
    attributes.main,
    inputs.main,
    polygonize.main,
    continents.main,
    intersection.main,
    outputs_land.main,
]
funcs_2 = [
    polygons.main,
    points.main,
    lines.main,
    outputs.main,
    cleanup.main,
]


def run_pool(world_views, funcs):
    with Pool() as pool:
        results = []
        for land in lands:
            for world in world_views:
                args = [land, world, *funcs]
                results.append(pool.apply_async(apply_funcs, args=args))
        for res in results:
            res.get()


if __name__ == "__main__":
    logger.info("starting")
    download.main()
    meta.main()
    preprocessing.main()
    run_pool([None], funcs_1)
    run_pool(world_views, funcs_2)
    cleanup.postprocessing()
    logger.info("finished")

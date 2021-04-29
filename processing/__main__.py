from pathlib import Path
from multiprocessing import Pool
from . import (download, inputs, attributes, polygonize,
               intersection, points, lines, outputs, cleanup)
from .utils import logging, LAND_URL, ADM0_URL

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_files = (cwd / '../inputs').resolve()
output_files = (cwd / '../outputs').resolve()


def download_inputs():
    if not (input_files / 'land/land_polygons.shp').is_file():
        download.main(LAND_URL, input_files / 'land')
    if not (input_files / 'adm0/adm0_lines.gpkg').is_file():
        download.main(ADM0_URL, input_files / 'adm0')


def import_inputs():
    layers = [
        ('land_polygons', 'land/land_polygons.shp', 3),
        ('adm0_lines', 'adm0/adm0_lines.gpkg', 2),
        ('adm0_points', 'adm0/adm0_points.gpkg', 1),
    ]
    results = []
    pool = Pool()
    for name, layer, geometry in layers:
        args = [name, input_files / layer, geometry]
        result = pool.apply_async(inputs.main, args=args)
        results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


def import_attributes():
    file = input_files / 'adm0/adm0_attributes.xlsx'
    attributes.main(file)


def export_outputs():
    layers = [
        ('adm0_polygons', '01'),
        ('adm0_lines', '02'),
        ('adm0_points', '01'),
    ]
    results = []
    pool = Pool()
    for name, layer in layers:
        args = [name, f'{name}_{layer}', output_files / f'{name}.gpkg']
        result = pool.apply_async(outputs.main, args=args)
        results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


def export_cleanup():
    layers = [
        'adm0_attributes',
        'adm0_lines_00',
        'adm0_lines_01',
        'adm0_lines_02',
        'adm0_points_00',
        'adm0_points_01',
        'adm0_polygons_00',
        'adm0_polygons_01',
        'land_polygons_00',
        'land_polygons_01',
    ]
    cleanup.main(layers)


if __name__ == '__main__':
    logger.info('Starting processing')
    download_inputs()
    import_inputs()
    import_attributes()
    polygonize.main()
    intersection.main()
    points.main()
    lines.main()
    export_outputs()
    export_cleanup()

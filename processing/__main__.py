from pathlib import Path
from multiprocessing import Pool
from . import (download, inputs, attributes, polygons, land,
               intersection, points, lines, outputs, cleanup)
from .utils import logging, LAND_URL, ADM0_URL

logger = logging.getLogger(__name__)

cwd = Path(__file__).parent
input_files = (cwd / '../inputs').resolve()
output_files = (cwd / '../outputs').resolve()
(input_files / 'adm0').mkdir(exist_ok=True, parents=True)
(input_files / 'land').mkdir(exist_ok=True, parents=True)
output_files.mkdir(exist_ok=True, parents=True)


def download_inputs():
    adm0_lines = (input_files / 'adm0/adm0_lines.gpkg')
    adm0_points = (input_files / 'adm0/adm0_points.gpkg')
    adm0_attributes = (input_files / 'adm0/adm0_attributes.xlsx')
    land_cpg = (input_files / 'land/land_polygons.cpg').is_file()
    land_dbf = (input_files / 'land/land_polygons.dbf').is_file()
    land_prj = (input_files / 'land/land_polygons.prj').is_file()
    land_shp = (input_files / 'land/land_polygons.shp').is_file()
    land_shx = (input_files / 'land/land_polygons.shx').is_file()
    if not adm0_lines.is_file():
        download.get_file(f'{ADM0_URL}/adm0_lines.gpkg', adm0_lines)
    if not adm0_points.is_file():
        download.get_file(f'{ADM0_URL}/adm0_points.gpkg', adm0_points)
    if not adm0_attributes.is_file():
        download.get_file(f'{ADM0_URL}/adm0_attributes.xlsx', adm0_attributes)
    if not land_cpg or not land_dbf or not land_prj or not land_shp or not land_shx:
        download.get_zip(LAND_URL, input_files / 'land')


def import_attributes():
    file = input_files / 'adm0/adm0_attributes.xlsx'
    attributes.main(file)


def import_inputs():
    layers = [
        ('land_polygons', 'land/land_polygons.shp'),
        ('adm0_lines', 'adm0/adm0_lines.gpkg'),
        ('adm0_points', 'adm0/adm0_points.gpkg'),
    ]
    results = []
    pool = Pool()
    for name, layer in layers:
        args = [name, input_files / layer]
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
        args = [name, f'{name}_{layer}', output_files / f'{name}.gpkg']
        result = pool.apply_async(outputs.main, args=args)
        results.append(result)
    pool.close()
    pool.join()
    for result in results:
        result.get()


if __name__ == '__main__':
    logger.info('starting')
    download_inputs()
    import_attributes()
    import_inputs()
    polygons.main()
    land.main()
    intersection.main()
    points.main()
    lines.main()
    export_outputs()
    cleanup.main()

import logging

DATABASE = 'adm0_template'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def apply_funcs(name, file, layer, *args):
    for func in args:
        func(name, file, layer)

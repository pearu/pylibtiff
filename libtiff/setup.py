
import sys
from os.path import join, basename, splitext
from glob import glob

from numpy.distutils import log
from distutils.dep_util import newer


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    package_name = 'libtiff'
    config = Configuration(package_name, parent_package, top_path)

    bitarray_path = 'bitarray-a1646c0/bitarray'

    # Add subpackages here:
    config.add_subpackage('bitarray', bitarray_path)
    config.add_subpackage('scripts')
    # eof add.

    # Add extensions here:
    config.add_extension('bitarray._bitarray',
                         join(bitarray_path, '_bitarray.c'))
    config.add_extension('bittools', join('src', 'bittools.c'))
    config.add_extension('tif_lzw', join('src', 'tif_lzw.c'))
    # eof add.

    return config

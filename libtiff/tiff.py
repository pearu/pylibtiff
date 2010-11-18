"""
tiff - implements a numpy.memmap based TIFF file reader and writer
allowing manipulating TIFF files that have sizes larger than
available memory in computer.

Usage:
>>> tiff = TIFFfile('<filename.(tif|lsm)>')
>>> samples, sample_names = tiff.get_samples()
>>> arr = tiff.get_tiff_array(sample_index=0, subfile_type=0)

>>> tiff = TIFFimage(data, description=<str>)
>>> tiff.write_file (<filename.tif>, compression='none'|'lzw')
>>> del tiff # flush data to disk
"""
# Author: Pearu Peterson
# Created: April 2010
from __future__ import division
__all__ = ['TIFFfile', 'TIFFimage', 'TiffArray']

import os
import sys
import time
import numpy

from .tiff_file import TIFFfile
from .tiff_image import TIFFimage
from .tiff_array import TiffArray

def main ():
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        raise ValueError('File %r does not exists' % (filename))

    t = TIFFfile(filename)

    t.show_memory_usage()

    e = t.IFD[0].entries[-1]
    assert e.is_lsm
    import lsm
    print lsm.lsmblock(e)
    print lsm.lsminfo(e, 0)
    #print lsm.filestructure(e)
    #print lsm.timestamps(e)
    #print lsm.channelwavelength(e)

if __name__ == '__main__':
    main()


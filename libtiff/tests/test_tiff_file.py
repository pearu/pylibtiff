
import os
import sys
import atexit
from tempfile import mktemp
from numpy import (uint8, uint16, uint32, uint64, int8, int16, int32,
                   int64, float32, float64, complex64, complex128,
                   array, ones)
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage

import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
def test_write_read():
    for compression in [None, 'lzw']:
        for itype in [uint8, uint16, uint32, uint64,
                      int8, int16, int32, int64,
                      float32, float64,
                      complex64, complex128]:
            image = array([[1, 2, 3], [4, 5, 6]], itype)
            fn = mktemp('.tif')

            if 0:
                tif = TIFF.open(fn, 'w')
                tif.write_image(image, compression=compression)
                tif.close()
            else:
                tif = TIFFimage(image)
                tif.write_file(fn, compression=compression)
                del tif

            tif = TIFFfile(fn)
            data, names = tif.get_samples()
            assert names == ['sample0'], repr(names)
            assert len(data) == 1, repr(len(data))
            assert image.dtype == data[0].dtype, repr(
                (image.dtype, data[0].dtype))
            assert (image == data[0]).all()
            tif.close()
            atexit.register(os.remove, fn)


def test_issue19():
    size = 1024 * 32  # 1GB

    # size = 1024*63  # almost 4GB, test takes about 60 seconds but succeeds
    image = ones((size, size), dtype=uint8)
    # print('image size:', image.nbytes / 1024**2, 'MB')
    fn = mktemp('issue19.tif')
    tif = TIFFimage(image)
    try:
        tif.write_file(fn)
    except OSError as msg:
        if 'Not enough storage is available to process this command'\
           in str(msg):
            # Happens in Appveyour CI
            del tif
            atexit.register(os.remove, fn)
            return
        else:
            raise
    del tif
    tif = TIFFfile(fn)
    tif.get_tiff_array()[:]  # expected failure
    tif.close()
    atexit.register(os.remove, fn)

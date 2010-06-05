import os
from tempfile import mktemp
from numpy import *
from libtiff import TIFFfile, TIFFimage

def test_write_read():
    for itype in [uint8, uint16, uint32, uint64, 
                  int8, int16, int32, int64,
                  float32, float64,
                  complex64, complex128]:
        image = array([[1,2,3], [4,5,6]], itype)
        fn = mktemp('.tif')
        tif = TIFFimage(image)
        tif.write_file(fn)
        del tif

        tif = TIFFfile(fn)
        data, names = tif.get_samples()
        assert names==['sample0'],`names`
        assert len(data)==1, `len(data)`
        assert image.dtype==data[0].dtype, `image.dtype,data[0].dtype`
        assert (image==data[0]).all()

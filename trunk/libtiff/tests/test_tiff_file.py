
import os
import atexit
from tempfile import mktemp
from numpy import *
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage

def test_write_read():

    for compression in [None, 'lzw']:
        for itype in [uint8, uint16, uint32, uint64, 
                      int8, int16, int32, int64,
                      float32, float64,
                      complex64, complex128]:
            image = array([[1,2,3], [4,5,6]], itype)
            fn = mktemp('.tif')

            if 0:
                tif = TIFF.open(fn,'w')
                tif.write_image(image, compression=compression)
                tif.close()
            else:
                tif = TIFFimage(image)
                tif.write_file(fn, compression=compression)
                del tif

            tif = TIFFfile(fn)
            data, names = tif.get_samples()
            assert names==['sample0'],`names`
            assert len(data)==1, `len(data)`
            assert image.dtype==data[0].dtype, `image.dtype, data[0].dtype`
            assert (image==data[0]).all()
            
            #os.remove(fn)
            atexit.register(os.remove, fn)

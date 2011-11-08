
import os
import atexit
from tempfile import mktemp
from numpy import *
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage

def test_simple_slicing():
    for planar_config in [1,2]:
        for compression in [None, 'lzw']:
            for itype in [uint8, uint16, uint32, uint64, 
                          int8, int16, int32, int64,
                          float32, float64,
                          complex64, complex128]:
                image = random.randint(0, 100, size=(10,6,7)).astype (itype)
                fn = mktemp('.tif')

                if 0:
                    if planar_config==2:
                        continue
                    tif = TIFF.open(fn,'w')
                    tif.write_image(image, compression=compression)
                    tif.close()
                else:
                    tif = TIFFimage(image)
                    tif.write_file(fn, compression=compression, planar_config=planar_config)
                    del tif

                tif = TIFFfile(fn)
                arr = tif.get_tiff_array()
                data = arr[:]
                assert len(data)==len (image), `len(data)`
                assert image.dtype==data.dtype, `image.dtype, data[0].dtype`
                assert (image==data).all()
                assert arr.shape==image.shape

                indices = [0, slice(None), slice (0,2), slice (0,5,2)]
                for i0 in indices[:1]:
                    for i1 in indices:
                        for i2 in indices:
                            sl = (i0, i1, i2)
                            assert (arr[sl]==image[sl]).all(),`sl`
                #os.remove(fn)
                atexit.register(os.remove, fn)

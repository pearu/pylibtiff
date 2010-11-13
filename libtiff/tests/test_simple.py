
import os
from tempfile import mktemp
from numpy import *
from libtiff import TIFF

def test_write_read():
    for itype in [uint8, uint16, uint32, uint64, 
                  int8, int16, int32, int64,
                  float32, float64,
                  complex64, complex128]:

        image = array([[1,2,3], [4,5,6]], itype)
        fn = mktemp('.tif')
        tif = TIFF.open(fn,'w')
        tif.write_image(image)
        tif.close()
        
        tif = TIFF.open(fn,'r')
        image2 = tif.read_image()
        tif.close()
        os.remove(fn)

        assert image.dtype==image2.dtype
        assert (image==image2).all()

def test_slicing():
    shape = (16, 16)
    image = random.randint(255, size=shape)
    
    for i in range(shape[0]):
        for j in range(shape[1]):
            image1 = image[:i+1,:j+1]
            fn = mktemp('.tif')
            tif = TIFF.open(fn,'w')
            tif.write_image(image1)
            tif.close()
        
            tif = TIFF.open(fn,'r')
            image2 = tif.read_image()
            tif.close()
            
            assert (image1==image2).all(),`i,j`

            os.remove(fn)

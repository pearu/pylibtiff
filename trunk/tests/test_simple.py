
import os
from tempfile import mktemp
from numpy import *
from libtiff import TIFF

def test_write_read():
    for itype in [uint8, uint16, uint32, uint32]:

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


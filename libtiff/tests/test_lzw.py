
import numpy
from tempfile import mktemp
from libtiff import TIFFfile, TIFF
from libtiff.tif_lzw import encode as c_encode, decode as c_decode

#def TIFFencode(arr):
#    fn = mktemp('.tif')
#    tif = TIFF.open(fn, 'w+')
#    tif.write_image(arr.view(numpy.uint8), compression='lzw')
#    tif.close()
#    tif = TIFFfile(fn)
#    data, names = tif.get_samples(leave_compressed=True)
#    return data[0][0]

def test_encode():
    for arr in [
        numpy.array([7,7,7,8,8,7,7,6,6], numpy.uint8),
        numpy.array(range(400000), numpy.uint8),
        numpy.array([1,3,7,15,31,63], numpy.uint8)]:

        rarr = c_encode(arr)
        arr2 = c_decode(rarr, arr.nbytes)
        assert arr2.nbytes == arr.nbytes and (arr2==arr).all(),`arr2,arr`




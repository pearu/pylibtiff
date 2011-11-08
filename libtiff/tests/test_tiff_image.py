import os
import atexit
from tempfile import mktemp
from numpy import *
from libtiff import TIFFfile, TIFFimage, TIFF

def test_rw_rgb():
    itype = uint8
    dt = dtype(dict(names = list('rgb'), formats = [itype]*3))
    
    image = zeros((2,3), dtype=dt)
    image['r'][:,0] = 250
    image['g'][:,1] = 251
    image['b'][:,2] = 252

    fn = mktemp('.tif')
    tif = TIFFimage(image)
    tif.write_file(fn,compression='lzw')#, samples='rgb')
    del tif

    tif = TIFFfile(fn)
    data, names = tif.get_samples()
    #os.remove(fn)
    atexit.register(os.remove, fn)
    print image
    print data

    assert itype == data[0].dtype, `itype, data[0].dtype`
    assert (image['r']==data[0]).all()
    assert (image['g']==data[1]).all()
    assert (image['b']==data[2]).all()
    

def test_write_read():
    for compression in ['none', 'lzw']:
        for itype in [uint8, uint16, uint32, uint64, 
                      int8, int16, int32, int64,
                      float32, float64,
                      complex64, complex128]:
            image = array([[1,2,3], [4,5,6]], itype)
            fn = mktemp('.tif')
            tif = TIFFimage(image)
            tif.write_file(fn, compression=compression)
            del tif
            
            tif = TIFFfile(fn)
            data, names = tif.get_samples()
            #os.remove(fn)
            atexit.register(os.remove, fn)
            assert names==['sample0'],`names`
            assert len(data)==1, `len(data)`
            assert image.dtype==data[0].dtype, `image.dtype,data[0].dtype`
            assert (image==data[0]).all()


def test_write_lzw():
    for itype in [uint8, uint16, uint32, uint64, 
                  int8, int16, int32, int64,
                  float32, float64,
                  complex64, complex128]:
        #image = array([[1,2,3], [4,5,6]], itype)
        image = array([range(10000)], itype)
        #image = array([[0]*14000], itype)
        fn = mktemp('.tif')
        tif = TIFFimage(image)
        tif.write_file(fn, compression='lzw')
        del tif

        #os.system('wc %s; echo %s' % (fn, image.nbytes))

        tif = TIFF.open(fn,'r')
        image2 = tif.read_image()
        tif.close()
        #os.remove(fn)
        atexit.register(os.remove, fn)
        for i in range(image.size):
            if image.flat[i] != image2.flat[i]:
                print `i, image.flat[i-5:i+5].view(dtype=uint8),image2.flat[i-5:i+5].view(dtype=uint8)`
                break

        assert image.dtype==image2.dtype
        assert (image==image2).all()

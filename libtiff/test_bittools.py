
import numpy
import bittools

def test_setgetbit():

    # bit-wise copy
    arr = numpy.array(range(256), dtype=numpy.float64)
    arr2 = numpy.zeros(arr.shape, dtype=arr.dtype)
    for i in range(arr.nbytes * 8):
        b = bittools.getbit(arr, i)
        bittools.setbit(arr2, i, b)
    assert (arr==arr2).all(),`arr,arr2`

    print 'ok'

def test_getword():
    arr = numpy.array([63330], dtype=numpy.uint16)
    print bittools.getword(arr, 1, arr.dtype.itemsize * 8-1)
    print 'ok'

if __name__=='__main__':
    test_setgetbit()
    test_getword()

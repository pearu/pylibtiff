
import numpy
from . import bittools


def tobinary(arr):
    return ''.join([str(bittools.getbit(arr, i))
                    for i in range(arr.nbytes * 8)])


def test_setgetbit():
    # bit-wise copy
    arr = numpy.array(list(range(256)), dtype=numpy.float64)
    arr2 = numpy.zeros(arr.shape, dtype=arr.dtype)
    for i in range(arr.nbytes * 8):
        b = bittools.getbit(arr, i)
        bittools.setbit(arr2, i, b)
    assert (arr == arr2).all(), repr((arr, arr2))


def test_setgetword():
    for dtype in [numpy.ubyte, numpy.int32, numpy.float64]:
        arr = numpy.array(list(range(-256, 256)), dtype=dtype)
        arr2 = numpy.zeros(arr.shape, dtype=arr.dtype)
        for i in range(arr.nbytes):
            word, next = bittools.getword(arr, i * 8, 8)
            bittools.setword(arr2, i * 8, 8, word)
        assert (arr == arr2).all(), repr((arr, arr2))


def test_wordbits():
    dtype = numpy.dtype(numpy.int_)
    for width in range(1, dtype.itemsize * 8 + 1):
        arr = numpy.array([17, 131, 235], dtype=dtype)
        arr2 = numpy.zeros((1 + width // 8), dtype=dtype)
        bstr = tobinary(arr)
        word, next = bittools.getword(arr, 0, width)
        if width > 7:
            assert word == arr[0], repr((width, word, arr[0], bstr, dtype))
        bittools.setword(arr2, 0, width, word)
        assert bittools.getword(arr2, 0, width)[0] == word
        assert tobinary(arr2)[:width] == bstr[:width], \
            repr((tobinary(arr2)[:width], bstr[:width]))


if __name__ == '__main__':
    test_setgetbit()
    test_setgetword()
    test_wordbits()

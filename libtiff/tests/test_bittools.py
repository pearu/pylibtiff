import numpy
import pytest

bittools = pytest.importorskip('libtiff.bittools')


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
    arange = numpy.arange(-256, 256)
    for dtype in [numpy.ubyte, numpy.int32, numpy.float64]:
        arr = arange.astype(dtype)
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


def test_getword_all_offsets_and_widths():
    arr = numpy.random.default_rng(0).integers(0, 256, 11).astype(numpy.uint8)
    bits = tobinary(arr)
    nbits = arr.nbytes * 8
    for width in range(0, 65):
        for index in range(0, nbits - width + 1):
            word, next = bittools.getword(arr, index, width)
            expected = int(bits[index:index + width][::-1] or '0', 2)
            assert (word, next) == (expected, index + width), (index, width)


def test_getword_at_end_of_array():
    # reading the last bits must not read past the end of the buffer
    arr = numpy.array([0xa5], dtype=numpy.uint8)
    assert bittools.getword(arr, 0, 8) == (0xa5, 8)
    assert bittools.getword(arr, 4, 4) == (0xa, 8)
    assert bittools.getword(arr, 8, 0) == (0, 8)


def test_setword_64bit_value():
    arr = numpy.zeros(2, dtype=numpy.uint64)
    value = 0xfedcba9876543210
    assert bittools.setword(arr, 64, 64, value) == 128
    assert arr[1] == value
    assert bittools.getword(arr, 64, 64) == (value, 128)
    assert bittools.getword(arr, 68, 32) == ((value >> 4) & 0xffffffff, 100)


@pytest.mark.parametrize('func', ['getbit', 'setbit', 'getword', 'setword'])
def test_missing_array(func):
    with pytest.raises(TypeError):
        getattr(bittools, func)()
    with pytest.raises(TypeError):
        getattr(bittools, func)(index=0)


@pytest.mark.parametrize('func', ['getbit', 'setbit', 'getword', 'setword'])
def test_not_an_array(func):
    with pytest.raises(TypeError):
        getattr(bittools, func)(b'abc', 0)


@pytest.mark.parametrize('index', [-1, -8, -2 ** 40, 16, 17, 2 ** 40])
def test_bit_index_out_of_range(index):
    arr = numpy.zeros(4, dtype=numpy.uint8)
    view = arr[1:3]
    with pytest.raises(IndexError):
        bittools.getbit(view, index)
    with pytest.raises(IndexError):
        bittools.setbit(view, index, 1)
    with pytest.raises(IndexError):
        bittools.setbit(view, index, 1, 1)  # opt=1 must not skip the checks
    with pytest.raises(IndexError):
        bittools.getword(view, index, 1)
    with pytest.raises(IndexError):
        bittools.setword(view, index, 1, 1)
    with pytest.raises(IndexError):
        bittools.setword(view, index, 1, 1, 1)
    assert not arr.any()


@pytest.mark.parametrize('index,width', [(0, 17), (9, 8), (16, 1), (0, -1)])
def test_word_out_of_range(index, width):
    arr = numpy.zeros(4, dtype=numpy.uint8)
    view = arr[1:3]
    with pytest.raises(IndexError):
        bittools.getword(view, index, width)
    with pytest.raises(IndexError):
        bittools.setword(view, index, width, 0xffff, 1)
    assert not arr.any()


def test_width_too_large():
    arr = numpy.zeros(16, dtype=numpy.uint8)
    with pytest.raises(ValueError):
        bittools.getword(arr, 0, 65)
    with pytest.raises(ValueError):
        bittools.setword(arr, 0, 65, 1)


def test_non_contiguous_array():
    arr = numpy.zeros(8, dtype=numpy.uint8)[::2]
    with pytest.raises(ValueError):
        bittools.getbit(arr, 0)
    with pytest.raises(ValueError):
        bittools.setword(arr, 0, 8, 1)


def test_read_only_array():
    arr = numpy.zeros(2, dtype=numpy.uint8)
    arr.flags.writeable = False
    assert bittools.getbit(arr, 0) == 0
    with pytest.raises(ValueError):
        bittools.setbit(arr, 0, 1)
    with pytest.raises(ValueError):
        bittools.setword(arr, 0, 8, 1)
    assert not arr.any()

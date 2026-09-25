
import gc
import sys
import tracemalloc
import weakref

import numpy
# from tempfile import mktemp
# from libtiff import TIFFfile, TIFF

import pytest

# when running inside source directory:
tif_lzw = pytest.importorskip('libtiff.tif_lzw')
c_encode = tif_lzw.encode
c_decode = tif_lzw.decode

# def TIFFencode(arr):
#    fn = mktemp('.tif')
#    tif = TIFF.open(fn, 'w+')
#    tif.write_image(arr.view(numpy.uint8), compression='lzw')
#    tif.close()
#    tif = TIFFfile(fn)
#    data, names = tif.get_samples(leave_compressed=True)
#    return data[0][0]


def test_encode():
    for arr in [
            numpy.array([7, 7, 7, 8, 8, 7, 7, 6, 6], numpy.uint8),
            numpy.array(list(range(400000))).astype(numpy.uint8),
            numpy.array([1, 3, 7, 15, 31, 63], numpy.uint8)]:

        rarr = c_encode(arr)
        arr2 = c_decode(rarr, arr.nbytes)
        assert arr2.nbytes == arr.nbytes and (arr2 == arr).all(), \
            repr((arr2, arr))


def _pack_codes(codes, nbits=9):
    """Pack LZW codes MSB-first with a fixed code width."""
    bits = ''.join(format(code, '0%sb' % nbits) for code in codes)
    bits += '0' * (-len(bits) % 8)
    return numpy.array([int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)],
                       dtype=numpy.uint8)


@pytest.mark.parametrize('size', list(range(11)))
@pytest.mark.parametrize('kind', ['random', 'constant'])
def test_roundtrip_small(size, kind):
    if kind == 'random':
        arr = numpy.random.default_rng(size).integers(0, 256, size).astype(numpy.uint8)
    else:
        arr = numpy.full(size, 7, dtype=numpy.uint8)
    enc = c_encode(arr)
    assert enc.dtype == numpy.uint8 and enc.ndim == 1
    dec = c_decode(enc, size)
    assert dec.dtype == numpy.uint8
    numpy.testing.assert_array_equal(dec, arr)
    # a larger size returns only the decoded bytes
    numpy.testing.assert_array_equal(c_decode(enc, size + 10), arr)
    # a smaller size returns the first bytes
    numpy.testing.assert_array_equal(c_decode(enc, size // 2), arr[:size // 2])


@pytest.mark.parametrize('kind', ['random', 'compressible'])
def test_roundtrip_large(kind):
    # random data expands, so the encoder output spans several 1MB chunks
    rng = numpy.random.default_rng(42)
    if kind == 'random':
        arr = rng.integers(0, 256, 3_000_000).astype(numpy.uint8)
    else:
        arr = rng.integers(0, 4, 3_000_000).astype(numpy.uint8)
    enc = c_encode(arr)
    numpy.testing.assert_array_equal(c_decode(enc, arr.nbytes), arr)


def test_encode_raw_bytes_of_any_dtype():
    arr = numpy.arange(1000, dtype='>u2')
    enc = c_encode(arr)
    numpy.testing.assert_array_equal(c_decode(enc, arr.nbytes),
                                     arr.view(numpy.uint8))


def test_non_contiguous_input():
    arr = numpy.arange(2000, dtype=numpy.uint8)[::3]
    enc = c_encode(arr)
    numpy.testing.assert_array_equal(enc, c_encode(arr.copy()))
    numpy.testing.assert_array_equal(c_decode(enc, arr.nbytes), arr)
    padded = numpy.zeros(2 * enc.nbytes, dtype=numpy.uint8)
    padded[::2] = enc
    numpy.testing.assert_array_equal(c_decode(padded[::2], arr.nbytes), arr)


def test_invalid_arguments():
    arr = numpy.arange(10, dtype=numpy.uint8)
    enc = c_encode(arr)
    with pytest.raises(TypeError):
        c_encode(b'abc')
    with pytest.raises(TypeError):
        c_encode(numpy.array([1, 2], dtype=object))
    with pytest.raises(TypeError):
        c_decode(enc)
    with pytest.raises(TypeError):
        c_decode(bytes(enc), 10)
    with pytest.raises(ValueError):
        c_decode(enc, -1)


@pytest.mark.parametrize('data', [[], [0x80]])
def test_decode_too_short(data):
    with pytest.raises(ValueError, match='too short'):
        c_decode(numpy.array(data, dtype=numpy.uint8), 10)


def test_decode_old_style_codes():
    with pytest.raises(ValueError, match='old-style'):
        c_decode(numpy.array([0, 1, 2, 3], dtype=numpy.uint8), 10)


@pytest.mark.parametrize('codes', [
    [65, 66, 257],  # does not start with CODE_CLEAR
    [256, 65, 300, 257],  # refers to a code that is not yet defined
    [256, 256, 256, 257],  # CODE_CLEAR followed by CODE_CLEAR
])
def test_decode_corrupt(codes):
    with pytest.raises(ValueError, match='corrupted'):
        c_decode(_pack_codes(codes), 100)


def test_decode_truncated_returns_prefix():
    arr = numpy.random.default_rng(1).integers(0, 16, 5000).astype(numpy.uint8)
    enc = c_encode(arr)
    for n in [2, 3, 10, enc.nbytes // 2, enc.nbytes - 2]:
        dec = c_decode(enc[:n], arr.nbytes)
        assert dec.nbytes < arr.nbytes
        numpy.testing.assert_array_equal(dec, arr[:dec.nbytes])


def test_decode_random_garbage():
    rng = numpy.random.default_rng(3)
    for n in range(2, 200):
        data = rng.integers(0, 256, n).astype(numpy.uint8)
        data[0] = 0x80  # start with CODE_CLEAR
        try:
            dec = c_decode(data, 1000)
        except ValueError:
            continue
        assert dec.nbytes <= 1000


def test_encode_result_not_leaked():
    # single chunk
    arr = numpy.zeros(1000, dtype=numpy.uint8)
    enc = c_encode(arr)
    other = numpy.zeros(1)
    assert sys.getrefcount(enc) == sys.getrefcount(other)
    ref = weakref.ref(enc)
    del enc
    gc.collect()
    assert ref() is None


def test_encode_chunks_not_leaked():
    # random data needs several internal chunks
    arr = numpy.random.default_rng(0).integers(0, 256, 3_000_000).astype(numpy.uint8)
    c_encode(arr)
    gc.collect()
    tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        for _ in range(5):
            c_encode(arr)
        gc.collect()
        after = tracemalloc.get_traced_memory()[0]
    finally:
        tracemalloc.stop()
    assert after - before < arr.nbytes

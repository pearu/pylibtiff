import os
import sys
import atexit
from tempfile import mktemp
import numpy
from numpy import (uint8, uint16, uint32, uint64, int8, int16, int32,
                   int64, float32, float64, array, zeros, dtype,
                   complex64, complex128, issubdtype, integer)
from libtiff import TIFFfile, TIFFimage, TIFF

import pytest

SUPPORTED_DTYPES = [uint8, uint16, uint32, uint64,
                    int8, int16, int32, int64,
                    float32, float64,
                    complex64, complex128]


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
def test_rw_rgb():
    itype = uint8
    dt = dtype(dict(names=list('rgb'), formats=[itype] * 3))

    image = zeros((2, 3), dtype=dt)
    image['r'][:, 0] = 250
    image['g'][:, 1] = 251
    image['b'][:, 2] = 252

    fn = mktemp('.tif')
    tif = TIFFimage(image)
    tif.write_file(fn, compression='lzw')  # , samples='rgb')
    del tif

    tif = TIFFfile(fn)
    data, names = tif.get_samples()
    tif.close()
    atexit.register(os.remove, fn)

    assert itype == data[0].dtype, repr((itype, data[0].dtype))
    assert (image['r'] == data[0]).all()
    assert (image['g'] == data[1]).all()
    assert (image['b'] == data[2]).all()


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
@pytest.mark.parametrize("itype", SUPPORTED_DTYPES)
@pytest.mark.parametrize("compression", ["none", "lzw"])
def test_write_read(compression, itype):
    image = array([[1, 2, 3], [4, 5, 6]], itype)
    fn = mktemp('.tif')
    tif = TIFFimage(image)
    tif.write_file(fn, compression=compression)
    del tif

    tif = TIFFfile(fn)
    data, names = tif.get_samples()
    tif.close()
    atexit.register(os.remove, fn)
    assert names == ['sample0'], repr(names)
    assert len(data) == 1, repr(len(data))
    assert image.dtype == data[0].dtype, repr(
        (image.dtype, data[0].dtype))
    assert (image == data[0]).all()


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
@pytest.mark.parametrize("itype", SUPPORTED_DTYPES)
def test_write_lzw(itype):
    if issubdtype(itype, integer):
        # avoid overflow failure from numpy for integer types
        image = array([list(range(10000))]).astype(itype)
    else:
        image = array([list(range(10000))], itype)
    fn = mktemp('.tif')
    tif = TIFFimage(image)
    tif.write_file(fn, compression='lzw')
    del tif

    # os.system('wc %s; echo %s' % (fn, image.nbytes))

    tif = TIFF.open(fn, 'r')
    image2 = tif.read_image()
    tif.close()
    atexit.register(os.remove, fn)
    for i in range(image.size):
        if image.flat[i] != image2.flat[i]:
            # print(repr((i, image.flat[i - 5:i + 5].view(dtype=uint8),
            #            image2.flat[i - 5:i + 5].view(dtype=uint8))))
            break

    assert image.dtype == image2.dtype
    assert (image == image2).all()


darwin_mmap_resize = pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")


def _read_ctypes_pages(fn):
    tif = TIFF.open(fn, 'r')
    try:
        return [page.copy() for page in tif.iter_images()]
    finally:
        tif.close()


@darwin_mmap_resize
@pytest.mark.parametrize("compression", ["none", "lzw"])
@pytest.mark.parametrize("planar_config", [1, 2])
def test_write_multipage_multistrip(tmp_path, compression, planar_config):
    image = numpy.arange(3 * 7 * 5, dtype=uint16).reshape(3, 7, 5)
    fn = str(tmp_path / 'stack.tif')
    # 3 rows per strip: 3 strips per page, the last one shorter
    TIFFimage(image).write_file(fn, compression=compression, strip_size=30,
                                planar_config=planar_config, validate=True)

    tif = TIFFfile(fn)
    assert len(tif.IFD) == 3
    assert tif.IFD[0].get_value('RowsPerStrip') == 3
    numpy.testing.assert_array_equal(tif.IFD[0].get_value('StripByteCounts') > 0, [True] * 3)
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image)
    tif.close()
    numpy.testing.assert_array_equal(_read_ctypes_pages(fn), image)


@darwin_mmap_resize
def test_write_list_of_images(tmp_path):
    images = [numpy.full((4, 6), i, dtype=float32) for i in range(3)]
    fn = str(tmp_path / 'list.tif')
    assert TIFFimage(images).write_file(fn) == 1.0
    numpy.testing.assert_array_equal(_read_ctypes_pages(fn), images)


@darwin_mmap_resize
def test_write_file_adds_extension(tmp_path):
    TIFFimage(zeros((2, 3), uint8)).write_file(str(tmp_path / 'image'))
    assert (tmp_path / 'image.tif').exists()
    TIFFimage(zeros((2, 3), uint8)).write_file(str(tmp_path / 'image2.TIFF'))
    assert (tmp_path / 'image2.TIFF').exists()


@darwin_mmap_resize
def test_write_lzw_compression_ratio(tmp_path):
    image = zeros((50, 50), uint8)
    fn = str(tmp_path / 'zeros.tif')
    ratio = TIFFimage(image).write_file(fn, compression='lzw')
    assert ratio > 1
    assert os.path.getsize(fn) < image.nbytes
    numpy.testing.assert_array_equal(_read_ctypes_pages(fn), [image])


def test_unsupported_input():
    with pytest.raises(NotImplementedError):
        TIFFimage(zeros((1, 2, 3, 4), uint8))
    with pytest.raises(NotImplementedError):
        TIFFimage((1, 2, 3))


@darwin_mmap_resize
def test_unsupported_compression(tmp_path):
    with pytest.raises(NotImplementedError):
        TIFFimage(zeros((2, 3), uint8)).write_file(str(tmp_path / 'image.tif'), compression='packbits')


@darwin_mmap_resize
@pytest.mark.xfail(strict=True, reason="TIFFimage.write_file fails for 1-D arrays (data is wrapped as [[data]])")
def test_write_1d(tmp_path):
    image = numpy.arange(10, dtype=uint8)
    fn = str(tmp_path / 'oned.tif')
    TIFFimage(image).write_file(fn)
    numpy.testing.assert_array_equal(_read_ctypes_pages(fn), [image[numpy.newaxis]])


@darwin_mmap_resize
def test_description(tmp_path):
    fn = str(tmp_path / 'description.tif')
    TIFFimage(zeros((2, 3), uint8), description='a longer description').write_file(fn)
    tif = TIFF.open(fn, 'r')
    assert tif.GetField('ImageDescription') == b'a longer description'
    assert tif.GetField('Software') == b'http://code.google.com/p/pylibtiff/'
    tif.close()
    tif = TIFFfile(fn)
    assert tif.IFD[0].get_value('ImageDescription') == b'a longer description\x00'
    tif.close()


@darwin_mmap_resize
@pytest.mark.xfail(strict=True, reason="TIFFimage writes ASCII values of up to 4 bytes out of line instead of inline")
def test_short_description(tmp_path):
    fn = str(tmp_path / 'description.tif')
    TIFFimage(zeros((2, 3), uint8), description='abc').write_file(fn)
    tif = TIFF.open(fn, 'r')
    assert tif.GetField('ImageDescription') == b'abc'
    tif.close()


@darwin_mmap_resize
@pytest.mark.xfail(strict=True, reason="TIFFimage writes str(bytes) for a bytes description")
def test_bytes_description(tmp_path):
    fn = str(tmp_path / 'description.tif')
    TIFFimage(zeros((2, 3), uint8), description=b'a longer description').write_file(fn)
    tif = TIFF.open(fn, 'r')
    assert tif.GetField('ImageDescription') == b'a longer description'
    tif.close()

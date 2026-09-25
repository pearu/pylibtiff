
import os
import sys
import atexit
from tempfile import mktemp
import numpy
from numpy import (uint8, uint16, uint32, uint64, int8, int16, int32,
                   int64, float32, float64, complex64, complex128,
                   array, ones)
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage

import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
def test_write_read():
    for compression in [None, 'lzw']:
        for itype in [uint8, uint16, uint32, uint64,
                      int8, int16, int32, int64,
                      float32, float64,
                      complex64, complex128]:
            image = array([[1, 2, 3], [4, 5, 6]], itype)
            fn = mktemp('.tif')

            if 0:
                tif = TIFF.open(fn, 'w')
                tif.write_image(image, compression=compression)
                tif.close()
            else:
                tif = TIFFimage(image)
                tif.write_file(fn, compression=compression)
                del tif

            tif = TIFFfile(fn)
            data, names = tif.get_samples()
            assert names == ['sample0'], repr(names)
            assert len(data) == 1, repr(len(data))
            assert image.dtype == data[0].dtype, repr(
                (image.dtype, data[0].dtype))
            assert (image == data[0]).all()
            tif.close()
            atexit.register(os.remove, fn)


def test_issue19():
    size = 1024 * 32  # 1GB

    # size = 1024*63  # almost 4GB, test takes about 60 seconds but succeeds
    image = ones((size, size), dtype=uint8)
    # print('image size:', image.nbytes / 1024**2, 'MB')
    fn = mktemp('issue19.tif')
    tif = TIFFimage(image)
    try:
        tif.write_file(fn)
    except OSError as msg:
        if 'Not enough storage is available to process this command'\
           in str(msg):
            # Happens in Appveyour CI
            del tif
            atexit.register(os.remove, fn)
            return
        else:
            raise
    del tif
    tif = TIFFfile(fn)
    tif.get_tiff_array()[:]  # expected failure
    tif.close()
    atexit.register(os.remove, fn)


darwin_mmap_resize = pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")


def _write_ctypes(fn, arr, rows_per_strip=None, description=None, mode='w', **kwargs):
    """Write arr with the libtiff ctypes wrapper."""
    tif = TIFF.open(fn, mode)
    if rows_per_strip is not None:
        tif.SetField('RowsPerStrip', rows_per_strip)
    if description is not None:
        tif.SetField('ImageDescription', description)
    tif.write_image(arr, **kwargs)
    tif.close()
    return str(fn)


@pytest.mark.parametrize("itype", [uint8, uint16, uint32, uint64, int8, int16, int32, int64,
                                   float32, float64, complex64, complex128])
def test_read_ctypes_file(tmp_path, itype):
    image = (numpy.arange(5 * 7).reshape(5, 7) - 10).astype(itype)
    fn = _write_ctypes(tmp_path / 'ctypes.tif', image, rows_per_strip=5)

    tif = TIFFfile(fn)
    assert not tif.is_lsm
    data, names = tif.get_samples()
    assert names == ['sample0']
    assert data[0].dtype == image.dtype
    numpy.testing.assert_array_equal(data[0], image[numpy.newaxis])
    arr = tif.get_tiff_array()
    assert arr.shape == (1, 5, 7)
    assert arr.dtype == image.dtype
    numpy.testing.assert_array_equal(arr[:], image[numpy.newaxis])
    tif.close()


@pytest.mark.xfail(strict=True, reason="TiffSamplePlane overflows uint16 (NEP 50) with the default RowsPerStrip "
                                       "when the tag is missing")
def test_read_ctypes_file_without_rows_per_strip(tmp_path):
    image = numpy.arange(5 * 7, dtype=uint16).reshape(5, 7)
    fn = _write_ctypes(tmp_path / 'ctypes.tif', image)
    tif = TIFFfile(fn)
    assert tif.IFD[0].get('RowsPerStrip') is None
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image[numpy.newaxis])
    tif.close()


@pytest.mark.xfail(strict=True, reason="The pure-Python reader ignores the Predictor tag")
@pytest.mark.parametrize("reader", ["get_samples", "get_tiff_array"])
def test_read_ctypes_lzw_predictor(tmp_path, reader):
    image = numpy.arange(5 * 7, dtype=uint16).reshape(5, 7) * 3
    fn = _write_ctypes(tmp_path / 'lzw.tif', image, rows_per_strip=5, compression='lzw')
    tif = TIFFfile(fn)
    assert tif.IFD[0].get_value('Predictor') == 2
    if reader == 'get_samples':
        data = tif.get_samples()[0][0]
    else:
        data = tif.get_tiff_array()[:]
    tif.close()
    numpy.testing.assert_array_equal(data, image[numpy.newaxis])


def test_read_big_endian_file(tmp_path):
    image = numpy.arange(5 * 7, dtype=uint16).reshape(5, 7) * 257
    fn = _write_ctypes(tmp_path / 'big_endian.tif', image, rows_per_strip=5, mode='wb')
    tif = TIFFfile(fn)
    assert tif.endian == 'big'
    assert tif.IFD[0].get_value('ImageWidth') == 7
    numpy.testing.assert_array_equal(tif.get_samples()[0][0], image[numpy.newaxis])
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image[numpy.newaxis])
    tif.close()


def test_read_rgb_ctypes_file(tmp_path):
    image = numpy.arange(4 * 6 * 3, dtype=uint8).reshape(4, 6, 3)
    fn = _write_ctypes(tmp_path / 'rgb.tif', image, rows_per_strip=4, write_rgb=True)
    tif = TIFFfile(fn)
    data, names = tif.get_samples()
    assert names == ['red', 'green', 'blue']
    for i in range(3):
        numpy.testing.assert_array_equal(data[i][0], image[..., i])
        numpy.testing.assert_array_equal(tif.get_tiff_array(sample_index=i)[0], image[..., i])
    with pytest.raises(IndexError):
        tif.get_tiff_array(sample_index=3)
    tif.close()


@pytest.mark.xfail(strict=True, reason="IFD entries with count > 1 that fit in 4 bytes are not read inline")
def test_read_inline_ascii_value(tmp_path):
    image = numpy.zeros((2, 3), uint8)
    tif = TIFF.open(tmp_path / 'artist.tif', 'w')
    tif.SetField('Artist', b'ab')
    tif.write_image(image)
    tif.close()
    tif = TIFFfile(str(tmp_path / 'artist.tif'))
    assert tif.IFD[0].get_value('Artist') == b'ab\x00'
    tif.close()


def test_use_memmap_false(tmp_path):
    image = numpy.arange(5 * 7, dtype=int16).reshape(5, 7)
    fn = _write_ctypes(tmp_path / 'ctypes.tif', image, rows_per_strip=5)
    tif = TIFFfile(fn, use_memmap=False)
    assert not isinstance(tif.data, numpy.memmap)
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image[numpy.newaxis])
    tif.close()


# TIFFfile.__del__ fails after a failed open, see test_close_after_failed_open
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_open_errors(tmp_path):
    with pytest.raises(ValueError, match='does not exist'):
        TIFFfile(str(tmp_path / 'missing.tif'))
    empty = tmp_path / 'empty.tif'
    empty.write_bytes(b'')
    with pytest.raises(ValueError, match='zero size'):
        TIFFfile(str(empty))
    bad = tmp_path / 'bad.tif'
    bad.write_bytes(b'XX*\x00\x08\x00\x00\x00')
    with pytest.raises(ValueError, match='byteorder'):
        TIFFfile(str(bad))
    bigtiff = tmp_path / 'bigtiff.tif'
    bigtiff.write_bytes(b'II+\x00\x08\x00\x00\x00' + bytes(8))
    with pytest.raises(ValueError, match='magic'):
        TIFFfile(str(bigtiff))
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((2, 2), uint8))
    with pytest.raises(NotImplementedError):
        TIFFfile(fn, mode='w')


@pytest.mark.xfail(strict=True, reason="TIFFfile.close fails when the header could not be parsed")
def test_close_after_failed_open(tmp_path):
    bad = tmp_path / 'bad.tif'
    bad.write_bytes(b'XX*\x00\x08\x00\x00\x00')
    tif = TIFFfile.__new__(TIFFfile)
    with pytest.raises(ValueError, match='byteorder'):
        tif.__init__(str(bad))
    try:
        tif.close()
    finally:
        # let TIFFfile.__del__ run cleanly when the object is collected later
        tif.__dict__.setdefault('IFD', [])


def test_ifd_values(tmp_path):
    image = numpy.zeros((5, 7), uint16)
    fn = _write_ctypes(tmp_path / 'ctypes.tif', image, rows_per_strip=5, compression='lzw')
    tif = TIFFfile(fn)
    assert repr(tif) == 'TIFFfile(%r)' % fn
    ifd = tif.IFD[0]
    assert len(ifd) == len(ifd.entries)
    assert ifd.get('ImageWidth').value == 7
    assert ifd.get('NoSuchTag') is None
    assert ifd.get_value('ImageLength') == 5
    assert ifd.get_value('Compression', human=True) == 'LZW'
    assert ifd.get_value('Predictor', human=True) == 'HorizontalDifferencing'
    assert ifd.get_value('PhotometricInterpretation', human=True) == 'BlackIsZero'
    assert ifd.get_value('PlanarConfiguration', human=True) == 'Chunky'
    assert ifd.get_value('Orientation', human=True) == 'TopLeft'
    # missing tags fall back to the TIFF defaults
    assert ifd.get_value('NewSubfileType') == 0
    assert ifd.get_value('SamplesPerPixel') == 1
    assert ifd.get_value('ResolutionUnit', human=True) == 'Inch'
    assert ifd.get_value('XResolution', 72) == 72
    numpy.testing.assert_array_equal(ifd.get_value('BitsPerSample'), [16])
    assert ifd.get_sample_names() == ['sample0']
    assert ifd.get_pixel_name() == 'pixel'
    assert ifd.get_sample_dtypes() == [numpy.dtype('<u2')]
    assert ifd.get_pixel_dtype() == numpy.dtype([('sample0', '<u2')])
    assert ifd.get_pixel_typename() == 'uint16'
    assert 'IFDEntry(tag=ImageWidth, value=' in str(ifd)
    assert 'IFDEntry(tag=Compression, value=' in ifd.human()
    tif.close()


@darwin_mmap_resize
def test_file_structure(tmp_path):
    image = numpy.arange(3 * 4 * 5, dtype=uint8).reshape(3, 4, 5)
    fn = str(tmp_path / 'stack.tif')
    # TIFFimage writes an empty description out of line, which check_memory_usage reports
    TIFFimage(image, description='a description').write_file(fn)
    tif = TIFFfile(fn)
    assert len(tif.IFD) == 3
    assert tif.get_subfile_types() == [0]
    assert tif.get_depth() == 3
    assert tif.get_depth(subfile_type=1) == 0
    assert tif.get_first_ifd() is tif.IFD[0]
    assert tif.get_first_ifd(subfile_type=1) is None
    assert tif.is_contiguous()
    assert tif.check_memory_usage(verbose=False)
    tif.close()


@darwin_mmap_resize
@pytest.mark.xfail(strict=True, reason="TIFFfile.get_contiguous reshapes as (depth, width, length)")
def test_get_contiguous(tmp_path):
    image = numpy.arange(3 * 4 * 5, dtype=uint8).reshape(3, 4, 5)
    fn = str(tmp_path / 'stack.tif')
    TIFFimage(image).write_file(fn)
    tif = TIFFfile(fn)
    numpy.testing.assert_array_equal(tif.get_contiguous(), image)
    tif.close()


def test_get_info_without_description(tmp_path):
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((5, 7), uint16), rows_per_strip=5)
    tif = TIFFfile(fn)
    info = tif.get_info().splitlines()
    tif.close()
    assert 'Number of subfile types: 1' in info
    assert 'Number of images: 1' in info
    assert 'ImageLength: 5' in info
    assert 'ImageWidth: 7' in info
    assert 'Compression: Uncompressed' in info


@pytest.mark.xfail(strict=True, reason="TIFFfile.get_info uses str methods on the bytes ImageDescription")
def test_get_info_with_description(tmp_path):
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((5, 7), uint16), rows_per_strip=5,
                       description=b'some description')
    tif = TIFFfile(fn)
    info = tif.get_info()
    tif.close()
    assert 'some description' in info


@pytest.mark.xfail(strict=True, reason="IFDEntry.human joins the bytes ImageDescription as str")
def test_ifd_human_with_description(tmp_path):
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((5, 7), uint16), rows_per_strip=5,
                       description=b'some description')
    tif = TIFFfile(fn)
    human = tif.IFD[0].human()
    tif.close()
    assert 'some description' in human


def test_pixel_sizes_without_description(tmp_path):
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((5, 7), uint16), rows_per_strip=5)
    tif = TIFFfile(fn)
    arr = tif.get_tiff_array()
    assert arr.get_pixel_sizes() == (1, 1)
    assert arr.get_voxel_sizes() == (1, 1, 1)
    assert arr.get_time() is None
    tif.close()


@pytest.mark.xfail(strict=True, reason="get_pixel_sizes/get_voxel_sizes use str methods on the bytes ImageDescription")
def test_pixel_sizes_from_description(tmp_path):
    fn = _write_ctypes(tmp_path / 'ctypes.tif', numpy.zeros((5, 7), uint16), rows_per_strip=5,
                       description=b'PixelSizeX 0.5 PixelSizeY 0.25 VoxelSizeZ 2')
    tif = TIFFfile(fn)
    ifd = tif.IFD[0]
    assert ifd.get_pixel_sizes() == (0.25, 0.5)
    assert ifd.get_voxel_sizes() == (2.0, 0.25, 0.5)
    tif.close()

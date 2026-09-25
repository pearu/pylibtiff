
import os
import sys
import atexit
from tempfile import mktemp
import numpy
from numpy import (uint8, uint16, uint32, uint64, int8, int16, int32,
                   int64, float32, float64, complex64, complex128, random)
from libtiff import TIFF
from libtiff import TIFFfile, TIFFimage

import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")
def test_simple_slicing():
    for planar_config in [1, 2]:
        for compression in [None, 'lzw']:
            for itype in [uint8, uint16, uint32, uint64,
                          int8, int16, int32, int64,
                          float32, float64,
                          complex64, complex128]:
                image = random.randint(0, 100, size=(10, 6, 7)).astype(itype)
                fn = mktemp('.tif')

                if 0:
                    if planar_config == 2:
                        continue
                    tif = TIFF.open(fn, 'w')
                    tif.write_image(image, compression=compression)
                    tif.close()
                else:
                    tif = TIFFimage(image)
                    tif.write_file(fn,
                                   compression=compression,
                                   planar_config=planar_config)
                    del tif

                tif = TIFFfile(fn)
                arr = tif.get_tiff_array()
                data = arr[:]
                assert len(data) == len(image), repr(len(data))
                assert image.dtype == data.dtype, repr((image.dtype,
                                                       data[0].dtype))
                assert (image == data).all()
                assert arr.shape == image.shape

                _indices = [0, slice(None), slice(0, 2), slice(0, 5, 2)]
                for _i0 in _indices[:1]:
                    for i1 in _indices:
                        for i2 in _indices:
                            sl = (_i0, i1, i2)
                            assert (arr[sl] == image[sl]).all(), repr(sl)
                tif.close()
                atexit.register(os.remove, fn)


darwin_mmap_resize = pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")


def _write_stack(fn, image, **kwargs):
    TIFFimage(image, description='a description').write_file(str(fn), **kwargs)
    return TIFFfile(str(fn))


@darwin_mmap_resize
def test_tiff_array_indexing(tmp_path):
    image = numpy.arange(4 * 5 * 6, dtype=int32).reshape(4, 5, 6)
    tif = _write_stack(tmp_path / 'stack.tif', image, strip_size=48)
    arr = tif.get_tiff_array()
    assert len(arr) == 4
    assert arr.shape == (4, 5, 6)
    assert arr.dtype == numpy.dtype('<i4')
    assert arr.nbytes == image.nbytes
    assert len(list(arr)) == 4
    numpy.testing.assert_array_equal(arr[2], image[2])
    numpy.testing.assert_array_equal(arr[1:3], image[1:3])
    numpy.testing.assert_array_equal(arr[::2], image[::2])
    numpy.testing.assert_array_equal(arr[()], image)
    numpy.testing.assert_array_equal(arr[(1,)], image[1])
    numpy.testing.assert_array_equal(arr[1, 2], image[1, 2])
    numpy.testing.assert_array_equal(arr[1, 2, 3], image[1, 2, 3])
    numpy.testing.assert_array_equal(arr[1, :, 3], image[1, :, 3])
    numpy.testing.assert_array_equal(arr[1:3, 1:4], image[1:3, 1:4])
    numpy.testing.assert_array_equal(arr[:, :, 2], image[:, :, 2])
    with pytest.raises(NotImplementedError):
        arr['a']
    tif.close()


@darwin_mmap_resize
def test_tiff_array_extend(tmp_path):
    image = numpy.arange(2 * 5 * 6, dtype=uint16).reshape(2, 5, 6)
    tif1 = _write_stack(tmp_path / 'stack1.tif', image)
    tif2 = _write_stack(tmp_path / 'stack2.tif', image + 100)
    arr = tif1.get_tiff_array()
    arr.extend(tif2.get_tiff_array())
    assert arr.shape == (4, 5, 6)
    numpy.testing.assert_array_equal(arr[:], numpy.concatenate([image, image + 100]))

    tif3 = _write_stack(tmp_path / 'stack3.tif', image.astype(uint8))
    with pytest.raises(TypeError, match='not homogeneous'):
        arr.append(tif3.get_tiff_array().planes[0])
    tif4 = _write_stack(tmp_path / 'stack4.tif', image[:, :4])
    with pytest.raises(TypeError, match='not homogeneous'):
        arr.append(tif4.get_tiff_array().planes[0])
    assert arr.shape == (4, 5, 6)
    for tif in [tif1, tif2, tif3, tif4]:
        tif.close()


@darwin_mmap_resize
def test_tiff_array_time(tmp_path):
    image = numpy.zeros((3, 2, 2), dtype=uint8)
    tif = _write_stack(tmp_path / 'stack.tif', image)
    tif.set_time([0.5, 1.5, 2.5])
    arr = tif.get_tiff_array()
    assert [arr.get_time(i) for i in range(3)] == [0.5, 1.5, 2.5]
    tif.close()

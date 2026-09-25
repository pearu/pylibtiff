import sys

import numpy
import pytest

from libtiff import TIFFfile, TIFFimage

pytestmark = pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")


def _write(fn, image, **kwargs):
    TIFFimage(image, description='a description').write_file(str(fn), **kwargs)
    return TIFFfile(str(fn))


@pytest.mark.parametrize("compression", ["none", "lzw"])
def test_rows(tmp_path, compression):
    image = numpy.arange(7 * 5, dtype=numpy.uint16).reshape(7, 5)
    # 3 rows per strip: 3 strips, the last one shorter
    tif = _write(tmp_path / 'image.tif', image, strip_size=30, compression=compression)
    plane = tif.get_tiff_array().planes[0]
    assert len(plane) == 7
    assert plane.shape == (7, 5)
    assert plane.strips_per_image == 3
    assert plane.rows_per_strip == 3
    assert plane.is_contiguous == (compression == 'none')
    assert 'shape=(7, 5)' in plane.get_topology()
    for row in range(7):
        numpy.testing.assert_array_equal(plane[row], image[row])
        numpy.testing.assert_array_equal(plane.get_row(row - 7), image[row])
    assert plane[3, 2] == image[3, 2]
    numpy.testing.assert_array_equal(plane[3, 1:4], image[3, 1:4])
    numpy.testing.assert_array_equal(plane.get_rows(4), image[4:5])
    numpy.testing.assert_array_equal(plane.get_rows(slice(1, 6, 2)), image[1:6:2])
    numpy.testing.assert_array_equal(plane.get_rows((2,)), image[2])
    numpy.testing.assert_array_equal(plane[2:5], image[2:5])
    numpy.testing.assert_array_equal(plane[()], image)
    numpy.testing.assert_array_equal(plane[1:3, 2], image[1:3, 2])
    with pytest.raises(IndexError):
        plane.get_row(8)
    with pytest.raises(IndexError):
        plane.get_row(-8)
    with pytest.raises(NotImplementedError):
        plane['a']
    tif.close()


@pytest.mark.xfail(strict=True, reason="TiffSamplePlane.get_row accepts row index == number of rows (off by one)")
def test_row_index_out_of_range(tmp_path):
    image = numpy.arange(7 * 5, dtype=numpy.uint16).reshape(7, 5)
    tif = _write(tmp_path / 'image.tif', image, strip_size=30)
    plane = tif.get_tiff_array().planes[0]
    with pytest.raises(IndexError):
        plane.get_row(7)
    tif.close()


def _rgb_image():
    dt = numpy.dtype(dict(names=list('rgb'), formats=[numpy.uint8] * 3))
    image = numpy.zeros((6, 5), dtype=dt)
    image['r'] = numpy.arange(30).reshape(6, 5)
    image['g'] = 100 + numpy.arange(30).reshape(6, 5)
    image['b'] = 200 + numpy.arange(30).reshape(6, 5) % 50
    return image


def test_rgb_samples(tmp_path):
    image = _rgb_image()
    tif = _write(tmp_path / 'rgb.tif', image)
    assert tif.IFD[0].get_sample_names() == ['sample0', 'sample1', 'sample2']
    for i, name in enumerate('rgb'):
        arr = tif.get_tiff_array(sample_index=i)
        assert arr.dtype == numpy.uint8
        numpy.testing.assert_array_equal(arr[0], image[name])
        numpy.testing.assert_array_equal(arr[0, 2], image[name][2])
    pixels = tif.get_tiff_array(sample_index=None)
    assert pixels.dtype.names == ('sample0', 'sample1', 'sample2')
    assert pixels.planes[0].sample_name == 'pixel'
    tif.close()


@pytest.mark.xfail(strict=True, reason="TiffSamplePlane ignores sample_index for compressed data")
def test_rgb_samples_lzw(tmp_path):
    image = _rgb_image()
    tif = _write(tmp_path / 'rgb.tif', image, compression='lzw')
    for i, name in enumerate('rgb'):
        numpy.testing.assert_array_equal(tif.get_tiff_array(sample_index=i)[0], image[name])
    tif.close()


def test_relative_time_from_description(tmp_path):
    image = numpy.zeros((2, 3), dtype=numpy.uint8)
    TIFFimage(image, description='RelativeTime 2.5 s').write_file(str(tmp_path / 'time.tif'))
    tif = TIFFfile(str(tmp_path / 'time.tif'))
    assert tif.get_tiff_array().get_time() == 2.5
    tif.close()


@pytest.mark.xfail(strict=True, reason="TiffSamplePlane parses str(bytes) of ImageDescription for RelativeTime")
def test_relative_time_at_end_of_description(tmp_path):
    image = numpy.zeros((2, 3), dtype=numpy.uint8)
    TIFFimage(image, description='RelativeTime 2.5').write_file(str(tmp_path / 'time.tif'))
    tif = TIFFfile(str(tmp_path / 'time.tif'))
    assert tif.get_tiff_array().get_time() == 2.5
    tif.close()


def test_set_time_overwrites(tmp_path, capsys):
    image = numpy.zeros((2, 3), dtype=numpy.uint8)
    tif = _write(tmp_path / 'image.tif', image)
    plane = tif.get_tiff_array().planes[0]
    assert plane.time is None
    plane.set_time(1.0)
    plane.set_time(2.0)
    assert plane.time == 2.0
    assert 'overwriting time value 1.0 with 2.0' in capsys.readouterr().out
    tif.close()

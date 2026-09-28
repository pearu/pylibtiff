import numpy
import pytest

from libtiff import TIFF, TiffFiles, TiffChannelsAndFiles


def _write_files(tmp_path, count, shape=(5, 7), prefix='image'):
    """Write single page TIFF files with the libtiff ctypes wrapper."""
    files = []
    images = []
    for i in range(count):
        image = numpy.arange(shape[0] * shape[1], dtype=numpy.uint16).reshape(shape) + 100 * i
        fn = str(tmp_path / ('%s%d.tif' % (prefix, i)))
        tif = TIFF.open(fn, 'w')
        tif.SetField('RowsPerStrip', shape[0])
        tif.write_image(image)
        tif.close()
        files.append(fn)
        images.append(image)
    return files, numpy.array(images)


def test_get_tiff_file(tmp_path):
    files, _ = _write_files(tmp_path, 2)
    tiff_files = TiffFiles(files)
    tiff = tiff_files.get_tiff_file(files[0])
    assert tiff.filename == files[0]
    # files are opened only once
    assert tiff_files.get_tiff_file(files[0]) is tiff
    tiff_files.close()
    assert tiff_files.tiff_files == {}


def test_get_info(tmp_path):
    files, _ = _write_files(tmp_path, 2)
    tiff_files = TiffFiles(files)
    info = tiff_files.get_info().splitlines()
    assert 'ImageWidth: 7' in info
    assert 'ImageLength: 5' in info
    tiff_files.close()


@pytest.mark.xfail(strict=True, reason="TiffFiles.get_tiff_array calls time_map.get() when time_map is None")
@pytest.mark.parametrize("assume_one_image_per_file", [False, True])
def test_get_tiff_array(tmp_path, assume_one_image_per_file):
    files, images = _write_files(tmp_path, 3)
    tiff_files = TiffFiles(files)
    arr = tiff_files.get_tiff_array(assume_one_image_per_file=assume_one_image_per_file)
    assert arr.shape == (3, 5, 7)
    numpy.testing.assert_array_equal(arr[:], images)
    tiff_files.close()


@pytest.mark.xfail(strict=True, reason="TiffFiles initialises its open file cache from time_map")
def test_get_tiff_array_with_time_map(tmp_path):
    files, images = _write_files(tmp_path, 2)
    time_map = {files[0]: [0.5], files[1]: [1.5]}
    tiff_files = TiffFiles(files, time_map=time_map)
    try:
        arr = tiff_files.get_tiff_array()
        numpy.testing.assert_array_equal(arr[:], images)
        assert [arr.get_time(0), arr.get_time(1)] == [0.5, 1.5]
    finally:
        # Drop anything that is not a TIFF file from the cache so that
        # TiffFiles.__del__ does not fail
        for key, value in list(tiff_files.tiff_files.items()):
            if not hasattr(value, 'close'):
                del tiff_files.tiff_files[key]
        tiff_files.close()


def test_channels_and_files_info(tmp_path):
    red, _ = _write_files(tmp_path, 1, prefix='red')
    green, _ = _write_files(tmp_path, 1, shape=(3, 4), prefix='green')
    channels = TiffChannelsAndFiles({'red': TiffFiles(red), 'green': TiffFiles(green)})
    info = channels.get_info().splitlines()
    assert 'Channel red:' in info
    assert 'Channel green:' in info
    assert 'ImageWidth: 7' in info
    assert 'ImageWidth: 4' in info
    channels.close()


@pytest.mark.xfail(strict=True, reason="TiffFiles.get_tiff_array calls time_map.get() when time_map is None")
def test_channels_and_files_get_tiff_array(tmp_path):
    red, red_images = _write_files(tmp_path, 2, prefix='red')
    green, green_images = _write_files(tmp_path, 2, shape=(3, 4), prefix='green')
    channels = TiffChannelsAndFiles({'red': TiffFiles(red), 'green': TiffFiles(green)})
    numpy.testing.assert_array_equal(channels.get_tiff_array('red')[:], red_images)
    numpy.testing.assert_array_equal(channels.get_tiff_array('green')[:], green_images)
    channels.close()

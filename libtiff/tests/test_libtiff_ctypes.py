import ctypes
import struct
import subprocess
import numpy as np
import pytest
import time
from libtiff import TIFFimage
import os
import sys

lt = pytest.importorskip('libtiff.libtiff_ctypes')


def test_issue69(tmp_path):
    itype = np.uint32
    image = np.array([[[1, 2, 3], [4, 5, 6]]], itype)
    fn = str(tmp_path / "issue69.tif")
    tif = TIFFimage(image)
    tif.write_file(fn)
    del tif
    tif = lt.TIFF3D.open(fn)
    tif.close()


# Hold the extenders created, as dereferencing any of them could cause a crash
extenders = []


def test_custom_tags(tmp_path):
    def _tag_write():
        a = lt.TIFF.open(tmp_path / "libtiff_test_custom_tags.tif", "w")

        a.SetField("ARTIST", b"MY NAME")
        a.SetField("LibtiffTestByte", 42)
        a.SetField("LibtiffTeststr", b"FAKE")
        a.SetField("LibtiffTestuint16", 42)
        a.SetField("LibtiffTestMultiuint32", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
        a.SetField("LibtiffTestBytes", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        a.SetField("XPOSITION", 42.0)
        a.SetField("PRIMARYCHROMATICITIES", (1.0, 2, 3, 4, 5, 6))

        arr = np.ones((512, 512), dtype=np.uint8)
        arr[:, :] = 255
        a.write_image(arr)

        print("Tag Write: SUCCESS")

    def _tag_read():
        a = lt.TIFF.open(tmp_path / "libtiff_test_custom_tags.tif", "r")

        tmp = a.read_image()
        assert tmp.shape == (512, 512), \
            "Image read was wrong shape (%r instead of (512,512))" % (tmp.shape,)
        tmp = a.GetField("XPOSITION")
        assert tmp == 42.0, "XPosition was not read as 42.0"
        tmp = a.GetField("ARTIST")
        assert tmp == b"MY NAME", "Artist was not read as 'MY NAME'"
        tmp = a.GetField("LibtiffTestByte")
        assert tmp == 42, "LibtiffTestbyte was not read as 42"
        tmp = a.GetField("LibtiffTestuint16")
        assert tmp == 42, "LibtiffTestuint16 was not read as 42"
        tmp = a.GetField("LibtiffTestMultiuint32")
        assert tmp == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], \
            "LibtiffTestMultiuint32 was not read as [1,2,3,4,5,6,7,8,9,10]"
        tmp = a.GetField("LibtiffTeststr")
        assert tmp == b"FAKE", "LibtiffTeststr was not read as 'FAKE'"
        tmp = a.GetField("LibtiffTestBytes")
        assert tmp == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tmp = a.GetField("PRIMARYCHROMATICITIES")
        assert tmp == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], \
            "PrimaryChromaticities was not read as [1.0,2.0,3.0,4.0,5.0,6.0]"
        print("Tag Read: SUCCESS")

    # Define a C structure that says how each tag should be used
    test_tags = [
        lt.TIFFFieldInfo(40100, 1, 1, lt.TIFFDataType.TIFF_BYTE, lt.FIELD_CUSTOM,
                         True, False, b"LibtiffTestByte"),
        lt.TIFFFieldInfo(40103, 10, 10, lt.TIFFDataType.TIFF_LONG, lt.FIELD_CUSTOM,
                         True, False, b"LibtiffTestMultiuint32"),
        lt.TIFFFieldInfo(40102, 1, 1, lt.TIFFDataType.TIFF_SHORT, lt.FIELD_CUSTOM,
                         True, False, b"LibtiffTestuint16"),
        lt.TIFFFieldInfo(40101, -1, -1, lt.TIFFDataType.TIFF_ASCII, lt.FIELD_CUSTOM,
                         True, False, b"LibtiffTeststr"),
        lt.TIFFFieldInfo(40104, lt.TIFF_VARIABLE2, lt.TIFF_VARIABLE2, lt.TIFFDataType.TIFF_BYTE,
                         lt.FIELD_CUSTOM, True, True, b"LibtiffTestBytes"),
    ]

    # Add tags to the libtiff library
    # Keep pointer to extender object, no gc:
    test_extender = lt.add_tags(test_tags)  # noqa: F841
    extenders.append(test_extender)
    _tag_write()
    _tag_read()


def test_tile_write(tmp_path):
    a = lt.TIFF.open(tmp_path / "libtiff_test_tile_write.tiff", "w")

    data_array = np.tile(list(range(500)), (1, 6)).astype(np.uint8)
    a.SetField("TileWidth", 512)
    a.SetField("TileLength", 528)
    # tile_width and tile_height is not set, write_tiles get these values from
    # TileWidth and TileLength tags
    assert a.write_tiles(data_array) == (512 * 528) * 6, "could not write tile images"  # 1D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 2D Arrays
    data_array = np.tile(list(range(500)), (2500, 6)).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528) == (512 * 528) * 5 * 6, \
        "could not write tile images"  # 2D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 3D Arrays, 3rd dimension as last dimension
    data_array = np.array(range(2500 * 3000 * 3))
    data_array = data_array.reshape(2500, 3000, 3).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528, None, True) == (512 * 528) * 5 * 6 * 3, \
        "could not write tile images"  # 3D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 3D Arrays, 3rd dimension as first dimension
    data_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528, None, True) == (512 * 528) * 5 * 6 * 3, \
        "could not write tile images"  # 3D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # Grayscale image with 3 depths
    data_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8)
    written_bytes = a.write_tiles(data_array, 512, 528)
    assert written_bytes == 512 * 528 * 5 * 6 * 3, \
        "could not write tile images, written_bytes: %s" % (written_bytes,)
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    print("Tile Write: SUCCESS")


def test_tile_read(tmp_path):
    test_tile_write(tmp_path)  # Create file first

    filename = tmp_path / "libtiff_test_tile_write.tiff"
    a = lt.TIFF.open(filename, "r")

    # 1D Arrays (doesn't make much sense to tile)
    a.SetDirectory(0)
    # expected tag values for the first image
    tags = [
        {"tag": "ImageWidth", "exp_value": 3000},
        {"tag": "ImageLength", "exp_value": 1},
        {"tag": "TileWidth", "exp_value": 512},
        {"tag": "TileLength", "exp_value": 528},
        {"tag": "BitsPerSample", "exp_value": 8},
        {"tag": "Compression", "exp_value": 1},
    ]

    # assert tag values
    for tag in tags:
        field_value = a.GetField(tag['tag'])
        assert field_value == tag['exp_value'], \
            repr((tag['tag'], tag['exp_value'], field_value))

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (1, 3000), "tile data read was the wrong shape"
    test_array = np.array(list(range(500)) * 6).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0, \
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # 2D Arrays (doesn't make much sense to tile)
    a.SetDirectory(1)
    # expected tag values for the second image
    tags = [
        {"tag": "ImageWidth", "exp_value": 3000},
        {"tag": "ImageLength", "exp_value": 2500},
        {"tag": "TileWidth", "exp_value": 512},
        {"tag": "TileLength", "exp_value": 528},
        {"tag": "BitsPerSample", "exp_value": 8},
        {"tag": "Compression", "exp_value": 1},
    ]

    # assert tag values
    for tag in tags:
        field_value = a.GetField(tag['tag'])
        assert field_value == tag['exp_value'], \
            repr((tag['tag'], tag['exp_value'], field_value))

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (2500, 3000), \
        "tile data read was the wrong shape"
    test_array = np.tile(list(range(500)),
                         (2500, 6)).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0, \
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # 3D Arrays, 3rd dimension as last dimension
    a.SetDirectory(2)
    # expected tag values for the third image
    tags = [
        {"tag": "ImageWidth", "exp_value": 3000},
        {"tag": "ImageLength", "exp_value": 2500},
        {"tag": "TileWidth", "exp_value": 512},
        {"tag": "TileLength", "exp_value": 528},
        {"tag": "BitsPerSample", "exp_value": 8},
        {"tag": "Compression", "exp_value": 1},
    ]

    # assert tag values
    for tag in tags:
        field_value = a.GetField(tag['tag'])
        assert field_value == tag['exp_value'], \
            repr(tag['tag'], tag['exp_value'], field_value)

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (2500, 3000, 3), \
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3)).reshape(
        2500, 3000, 3).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0, \
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # 3D Arrays, 3rd dimension as first dimension
    a.SetDirectory(3)
    # expected tag values for the third image
    tags = [
        {"tag": "ImageWidth", "exp_value": 3000},
        {"tag": "ImageLength", "exp_value": 2500},
        {"tag": "TileWidth", "exp_value": 512},
        {"tag": "TileLength", "exp_value": 528},
        {"tag": "BitsPerSample", "exp_value": 8},
        {"tag": "Compression", "exp_value": 1},
    ]

    # assert tag values
    for tag in tags:
        field_value = a.GetField(tag['tag'])
        assert field_value == tag['exp_value'], \
            repr(tag['tag'], tag['exp_value'], field_value)

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (3, 2500, 3000), \
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3))
    test_array = test_array.reshape(3, 2500, 3000).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0, \
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # Grayscale image with 3 depths
    a.SetDirectory(4)

    # expected tag values for the third image
    tags = [
        {"tag": "ImageWidth", "exp_value": 3000},
        {"tag": "ImageLength", "exp_value": 2500},
        {"tag": "TileWidth", "exp_value": 512},
        {"tag": "TileLength", "exp_value": 528},
        {"tag": "BitsPerSample", "exp_value": 8},
        {"tag": "Compression", "exp_value": 1},
        {"tag": "ImageDepth", "exp_value": 3}
    ]

    # assert tag values
    for tag in tags:
        field_value = a.GetField(tag['tag'])
        assert field_value == tag['exp_value'], \
            repr([tag['tag'], tag['exp_value'], field_value])

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (3, 2500, 3000), \
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0, \
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    print("Tile Read: SUCCESS")


def test_read_one_tile(tmp_path):
    test_tile_write(tmp_path)  # Create file first

    filename = tmp_path / "libtiff_test_tile_write.tiff"
    tiff = lt.TIFF.open(filename, "r")

    # the first image is 1 pixel high
    tile = tiff.read_one_tile(0, 0)
    assert tile.shape == (1, 512), repr(tile.shape)

    # second image, 3000 x 2500
    tiff.SetDirectory(1)
    tile = tiff.read_one_tile(0, 0)
    assert tile.shape == (528, 512), repr(tile.shape)

    tile = tiff.read_one_tile(512, 528)
    assert tile.shape == (528, 512), repr(tile.shape)

    # test tile on the right border
    tile = tiff.read_one_tile(2560, 528)
    assert tile.shape == (528, 440), repr(tile.shape)

    # test tile on the bottom border
    tile = tiff.read_one_tile(512, 2112)
    assert tile.shape == (388, 512), repr(tile.shape)

    # test tile on the right and bottom borders
    tile = tiff.read_one_tile(2560, 2112)
    assert tile.shape == (388, 440), repr(tile.shape)

    # test x and y values not multiples of the tile width and height
    tile = tiff.read_one_tile(530, 600)
    assert tile[0][0] == 12, tile[0][0]

    # test negative x
    try:
        tiff.read_one_tile(-5, 0)
        raise AssertionError(
            "An exception must be raised with invalid (x, y) values")
    except ValueError as inst:
        assert str(inst) == "Invalid x value", inst

    # test y greater than the image height
    try:
        tiff.read_one_tile(0, 5000)
        raise AssertionError(
            "An exception must be raised with invalid (x, y) values")
    except ValueError as inst:
        assert str(inst) == "Invalid y value", inst

    # RGB image sized 3000 x 2500, PLANARCONFIG_SEPARATE
    tiff.SetDirectory(3)
    tile = tiff.read_one_tile(0, 0)
    assert tile.shape == (3, 528, 512), repr(tile.shape)
    # get the tile on the lower bottom corner
    tile = tiff.read_one_tile(2999, 2499)
    assert tile.shape == (3, 388, 440), repr(tile.shape)

    # Grayscale image sized 3000 x 2500, 3 depths
    tiff.SetDirectory(4)
    tile = tiff.read_one_tile(0, 0)
    assert tile.shape == (3, 528, 512), repr(tile.shape)
    # get the tile on the lower bottom corner
    tile = tiff.read_one_tile(2999, 2499)
    assert tile.shape == (3, 388, 440), repr(tile.shape)


def test_tiled_image_read(tmp_path):
    """
    Tests opening a tiled image
    """
    test_tile_write(tmp_path)  # Create file first
    filename = tmp_path / "libtiff_test_tile_write.tiff"

    def assert_image_tag(tiff, tag_name, expected_value):
        value = tiff.GetField(tag_name)
        assert value == expected_value, \
            ('%s expected to be %d, but it\'s %d'
             % (tag_name, expected_value, value))

    tiff = lt.TIFF.open(filename, "r")

    # sets the current image to the second image
    tiff.SetDirectory(1)
    # test tag values
    assert_image_tag(tiff, 'ImageWidth', 3000)
    assert_image_tag(tiff, 'ImageLength', 2500)
    assert_image_tag(tiff, 'TileWidth', 512)
    assert_image_tag(tiff, 'TileLength', 528)
    assert_image_tag(tiff, 'BitsPerSample', 8)
    assert_image_tag(tiff, 'Compression', lt.COMPRESSION_NONE)  # noqa: F821

    # read the image to a NumPy array
    arr = tiff.read_image()
    # test image NumPy array dimensions
    assert arr.shape[0] == 2500, \
        'Image width expected to be 2500, but it\'s %d' % (arr.shape[0])
    assert arr.shape[1] == 3000, \
        'Image height expected to be 3000, but it\'s %d' % (arr.shape[1])

    # generates the same array that was generated for the image
    data_array = np.array(list(range(500)) * 6).astype(np.uint8)
    # tests if the array from the read image is the same of the original image
    assert (data_array == arr).all(), \
        'The read tiled image is different from the generated image'


def test_tags_write(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_tags_write.tiff', mode='w')
    tmp = tiff.SetField("Artist", b"A Name")
    assert tmp == 1, "Tag 'Artist' was not written properly"
    tmp = tiff.SetField("DocumentName", b"")
    assert tmp == 1, "Tag 'DocumentName' with empty string was not written properly"
    tmp = tiff.SetField("PrimaryChromaticities", [1, 2, 3, 4, 5, 6])
    assert tmp == 1, "Tag 'PrimaryChromaticities' was not written properly"
    tmp = tiff.SetField("BitsPerSample", 8)
    assert tmp == 1, "Tag 'BitsPerSample' was not written properly"
    tmp = tiff.SetField("ColorMap", [[x * 256 for x in range(256)]] * 3)
    assert tmp == 1, "Tag 'ColorMap' was not written properly"

    arr = np.zeros((100, 100), np.uint8)
    tiff.write_image(arr)

    print("Tag Write: SUCCESS")


def test_tags_read(tmp_path):
    test_tags_write(tmp_path)

    filename = tmp_path / 'libtiff_tags_write.tiff'
    tiff = lt.TIFF.open(filename)
    tmp = tiff.GetField("Artist")
    assert tmp == b"A Name", "Tag 'Artist' did not read the correct value (" \
        "Got '%s'; Expected 'A Name')" % (tmp,)
    tmp = tiff.GetField("DocumentName")
    assert tmp == b"", "Tag 'DocumentName' did not read the correct value (" \
        "Got '%s'; Expected empty string)" % (tmp,)
    tmp = tiff.GetField("PrimaryChromaticities")
    assert tmp == [1, 2, 3, 4, 5, 6], \
        "Tag 'PrimaryChromaticities' did not read the " \
        "correct value (Got '%r'; Expected '[1,2,3,4,5,6]'" % (tmp,)
    tmp = tiff.GetField("BitsPerSample")
    assert tmp == 8, "Tag 'BitsPerSample' did not read the correct value (" \
                     "Got %s; Expected 8)" % (str(tmp),)
    tmp = tiff.GetField("ColorMap")
    try:
        assert len(tmp) == 3, \
            f"Tag 'ColorMap' should be three arrays, found {len(tmp)}"
        assert len(tmp[0]) == 256, \
            f"Tag 'ColorMap' should be three arrays of 256 elements, found {len(tmp[0])} elements"
        assert len(tmp[1]) == 256, \
            f"Tag 'ColorMap' should be three arrays of 256 elements, found {len(tmp[1])} elements"
        assert len(tmp[2]) == 256, \
            f"Tag 'ColorMap' should be three arrays of 256 elements, found {len(tmp[2])} elements"
    except TypeError:
        print("Tag 'ColorMap' has the wrong shape of 3 arrays of 256 elements each")
        return

    print("Tag Read: SUCCESS")


def test_write(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = _i + 10 * j
    print(arr)
    tiff.write_image(arr)
    del tiff


def test_read(tmp_path):
    test_write(tmp_path)

    filename = tmp_path / 'libtiff_test_write.tiff'
    print('Trying to open', filename, '...', end=' ')
    tiff = lt.TIFF.open(filename)
    print('Trying to show info ...\n', '-' * 10)
    print(tiff.info())
    print('-' * 10, 'ok')
    print('Trying show images ...')
    t = time.time()
    i = 0
    for image in tiff.iter_images(verbose=True):
        print(image.min(), image.max(), image.mean())
        i += 1
    print('\tok', (time.time() - t) * 1e3, 'ms', i, 'images')


def test_write_float(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6), np.float64)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[i, j] = i + 10 * j
    print(arr)
    tiff.write_image(arr)
    del tiff

    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()
    print(arr2)


def test_write_rgba(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6, 4), np.uint8)
    for i in np.ndindex(*arr.shape):
        arr[i] = 20 * i[0] + 10 * i[1] + i[2]
    print(arr)
    tiff.write_image(arr, write_rgb=True)
    del tiff

    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()
    print(arr2)

    np.testing.assert_array_equal(arr, arr2)


def test_tree(tmp_path):
    # Write a TIFF image with the following tree structure:
    # Im0 --SubIFD--> Im0,1 ---> Im0,2 ---> Im0,3
    #  |
    #  V
    # Im1
    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for i in np.ndindex(*arr.shape):
        arr[i] = i[0] + 20 * i[1]
    print(arr)
    n = 3
    tiff.SetField("SubIFD", [0] * n)
    tiff.write_image(arr)
    for i in range(n):
        arr[0, 0] = i
        tiff.write_image(arr)

    arr[0, 0] = 255
    tiff.write_image(arr)
    del tiff

    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    n = 0
    for im in tiff.iter_images(verbose=True):
        print(im)
        n += 1

    assert n == 2


def test_copy(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_compression.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = 1 + _i + 10 * j
    # from scipy.stats import poisson
    # arr = poisson.rvs (arr)
    tiff.SetField('ImageDescription', b'Hey\nyou')
    tiff.write_image(arr, compression='lzw')
    del tiff

    tiff = lt.TIFF.open(tmp_path / 'libtiff_test_compression.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()

    assert (arr == arr2).all(), 'arrays not equal'

    for compression in ['none', 'lzw', 'deflate', 'adobe_deflate']:
        for sampleformat in ['int', 'uint', 'float']:
            for bitspersample in [128, 64, 32, 16, 8]:
                dtype_name = f"{sampleformat}{bitspersample}"
                if not hasattr(np, dtype_name):  # Skip non existing types
                    continue
                print(f"Testing convertion to {dtype_name}")
                # With compression, less data types supported
                if compression != 'none' and bitspersample > 32:
                    continue
                # print compression, sampleformat, bitspersample
                if compression == 'deflate':
                    # Redirect C-level stderr to capture the warning:
                    # "TIFFWriteDirectorySec: Warning, Creating TIFF with legacy Deflate codec identifier,
                    # COMPRESSION_ADOBE_DEFLATE is more widely supported."
                    # This warning occurs when using 'deflate' compression.
                    stderr_fileno = sys.stderr.fileno()
                    stderr_save = os.dup(stderr_fileno)
                    pipe_out, pipe_in = os.pipe()
                    os.dup2(pipe_in, stderr_fileno)

                    try:
                        tiff.copy(tmp_path / 'libtiff_test_copy2.tiff',
                                  compression=compression,
                                  imagedescription=b'hoo',
                                  sampleformat=sampleformat,
                                  bitspersample=bitspersample)
                    finally:
                        os.close(pipe_in)
                        # Restore stderr
                        os.dup2(stderr_save, stderr_fileno)
                        os.close(stderr_save)

                    # Read from the pipe
                    with os.fdopen(pipe_out) as f:
                        stderr_output = f.read()

                    assert 'legacy Deflate codec' in stderr_output
                else:
                    tiff.copy(tmp_path / 'libtiff_test_copy2.tiff',
                              compression=compression,
                              imagedescription=b'hoo',
                              sampleformat=sampleformat,
                              bitspersample=bitspersample)
                tiff2 = lt.TIFF.open(tmp_path / 'libtiff_test_copy2.tiff', mode='r')
                arr3 = tiff2.read_image()
                assert (arr == arr3).all(), 'arrays not equal %r' % (
                    (compression, sampleformat, bitspersample),)
    print('test copy ok')


# The TAG_TEST_DATA_BASE dictionary is used to test setting and getting TIFF
# tags.
TAG_TEST_DATA_BASE = {
    'uint16': {
        'ctype': ctypes.c_uint16,
        'values': [
            (lt.TIFFTAG_SAMPLEFORMAT, 'SampleFormat', lt.SAMPLEFORMAT_INT),
            (lt.TIFFTAG_SAMPLEFORMAT, 'SampleFormat', lt.SAMPLEFORMAT_UINT),
            (lt.TIFFTAG_COMPRESSION, 'Compression', lt.COMPRESSION_LZW),
            (lt.TIFFTAG_ORIENTATION, 'Orientation', lt.ORIENTATION_TOPLEFT),
            (lt.TIFFTAG_THRESHHOLDING, 'Threshholding', lt.THRESHHOLD_BILEVEL),
            (lt.TIFFTAG_FILLORDER, 'FillOrder', lt.FILLORDER_MSB2LSB),
            (lt.TIFFTAG_BITSPERSAMPLE, 'BitsPerSample', 8),
        ]
    },
    'uint32': {
        'ctype': ctypes.c_uint32,
        'values': [
            (lt.TIFFTAG_IMAGEWIDTH, 'ImageWidth', 256),
            (lt.TIFFTAG_IMAGELENGTH, 'ImageLength', 256),
            (lt.TIFFTAG_SUBFILETYPE, 'SubfileType', lt.FILETYPE_REDUCEDIMAGE),
            (lt.TIFFTAG_TILEWIDTH, 'TileWidth', 256),
            (lt.TIFFTAG_TILELENGTH, 'TileLength', 256),
            (lt.TIFFTAG_IMAGEWIDTH, 'ImageWidth', 128),
        ]
    },
    'float': {
        'ctype': ctypes.c_float,
        'set_wrapper': ctypes.c_double,
        'values': [
            (lt.TIFFTAG_XRESOLUTION, 'XResolution', 88.0),
            (lt.TIFFTAG_YRESOLUTION, 'YResolution', 88.0),
            (lt.TIFFTAG_XPOSITION, 'XPosition', 88.0),
            (lt.TIFFTAG_YPOSITION, 'YPosition', 88.0),
        ]
    },
    'double': {
        'ctype': ctypes.c_double,
        'set_wrapper': ctypes.c_double,
        'values': [
            (lt.TIFFTAG_SMAXSAMPLEVALUE, 'SMaxSampleValue', 255.0),
            (lt.TIFFTAG_SMINSAMPLEVALUE, 'SMinSampleValue', 0.0),
        ]
    },
    'string': {
        'ctype': ctypes.c_char_p,
        'values': [
            (lt.TIFFTAG_ARTIST, 'Artist', b"test string"),
            (lt.TIFFTAG_DATETIME, 'DateTime', b"test string"),
            (lt.TIFFTAG_HOSTCOMPUTER, 'HostComputer', b"test string"),
            (lt.TIFFTAG_IMAGEDESCRIPTION, 'ImageDescription', b"test string"),
            (lt.TIFFTAG_MAKE, 'Make', b"test string"),
            (lt.TIFFTAG_MODEL, 'Model', b"test string"),
            (lt.TIFFTAG_SOFTWARE, 'Software', b"test string"),
        ]
    }
}


def _get_default_tag_values(tmp_path, base_data):
    ltc = lt.libtiff
    tiff = lt.TIFF.open(tmp_path / 'default_values.tiff', mode='w')
    try:
        defaults = {}

        data_holders = {
            'uint16': ctypes.c_uint16(0),
            'uint32': ctypes.c_uint32(0),
            'float': ctypes.c_float(0.0),
            'double': ctypes.c_double(0.0),
            'string': ctypes.c_char_p(b''),
        }

        for type_name, test_data in base_data.items():
            for tag_const, _, _ in test_data['values']:
                if tag_const in defaults:
                    continue  # Already checked

                data_holder = data_holders[type_name]
                p_data_holder = ctypes.byref(data_holder)

                if ltc.TIFFGetFieldDefaulted(tiff, tag_const, p_data_holder):
                    defaults[tag_const] = data_holder.value
                else:
                    defaults[tag_const] = None
        # manually add missing default
        defaults[lt.TIFFTAG_SAMPLEFORMAT] = 1
        return defaults
    finally:
        tiff.close()


@pytest.fixture(scope='session')
def tag_test_data(tmp_path_factory):
    """Get dictionary of default TIFF tag values.

    This fixture generates the dictionary of tag defaults
    by accessing a real TIFF file. This avoids hardcoding the defaults and
    makes the tests more robust to changes in libtiff.
    """
    tmpdir = tmp_path_factory.mktemp("tag_defaults")
    default_values = _get_default_tag_values(tmpdir, TAG_TEST_DATA_BASE)

    new_tag_test_data = {}
    for type_name, test_data in TAG_TEST_DATA_BASE.items():
        new_tag_test_data[type_name] = {
            'ctype': test_data['ctype'],
            'values': []
        }
        if 'set_wrapper' in test_data:
            new_tag_test_data[type_name]['set_wrapper'] = test_data['set_wrapper']

        for tag_const, tag_name, value in test_data['values']:
            new_tag_test_data[type_name]['values'].append(
                (tag_const, tag_name, value, default_values.get(tag_const))
            )
    return new_tag_test_data


def _get_tiff_data_case(type_name, tmp_path, tag_test_data):
    tiff = lt.TIFF.open(tmp_path / f'libtiff_set_get_field_lowlevel_{type_name}.tiff', mode='w')

    data_holders = {
        'uint16': ctypes.c_uint16(0),
        'uint32': ctypes.c_uint32(0),
        'float': ctypes.c_float(0.0),
        'double': ctypes.c_double(0.0),
        'string': ctypes.c_char_p(b''),
    }
    data_holders_defaulted = {
        'uint16': ctypes.c_uint16(0),
        'uint32': ctypes.c_uint32(0),
        'float': ctypes.c_float(0.0),
        'double': ctypes.c_double(0.0),
        'string': ctypes.c_char_p(b''),
    }

    test_data = tag_test_data[type_name]
    data = data_holders[type_name]
    data_defaulted = data_holders_defaulted[type_name]

    return tiff, test_data, data, data_defaulted


@pytest.mark.parametrize("type_name", TAG_TEST_DATA_BASE.keys())
def test_set_get_field_lowlevel(type_name, tag_test_data, tmp_path):
    ltc = lt.libtiff
    tiff, test_data, data, data_defaulted = _get_tiff_data_case(type_name, tmp_path, tag_test_data)

    try:
        p_data = ctypes.byref(data)
        p_data_defaulted = ctypes.byref(data_defaulted)
        set_wrapper = test_data.get('set_wrapper')

        processed_tags = set()
        for tag_const, _tag_name, value, default_value in test_data['values']:
            if tag_const not in processed_tags:
                # Check the default value
                if default_value is not None:
                    assert ltc.TIFFGetFieldDefaulted(tiff, tag_const, p_data_defaulted)
                    assert data_defaulted.value == default_value
                processed_tags.add(tag_const)

            set_value = value
            if set_wrapper:
                set_value = set_wrapper(value)

            assert ltc.TIFFSetField(tiff, tag_const, set_value)
            assert ltc.TIFFGetField(tiff, tag_const, p_data)
            assert data.value == value
            assert ltc.TIFFGetFieldDefaulted(tiff, tag_const, p_data_defaulted)
            assert data_defaulted.value == value
    finally:
        tiff.close()


@pytest.fixture
def colormap_test_data(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_set_get_field_lowlevel_colormap.tiff', mode='w')
    try:
        tiff.SetField('BitsPerSample', 8)
        # Test tags with count > 1
        # Create three arrays of 256 16-bit integers
        colormap_red = (ctypes.c_uint16 * 256)(*range(256))
        colormap_green = (ctypes.c_uint16 * 256)(*range(256))
        colormap_blue = (ctypes.c_uint16 * 256)(*range(256))

        # Create pointers to receive colormap data
        p_colormap_red = ctypes.POINTER(ctypes.c_uint16)()
        p_colormap_green = ctypes.POINTER(ctypes.c_uint16)()
        p_colormap_blue = ctypes.POINTER(ctypes.c_uint16)()

        p_colormap_red_defaulted = ctypes.POINTER(ctypes.c_uint16)()
        p_colormap_green_defaulted = ctypes.POINTER(ctypes.c_uint16)()
        p_colormap_blue_defaulted = ctypes.POINTER(ctypes.c_uint16)()

        yield (
            tiff,
            colormap_red, colormap_green, colormap_blue,
            p_colormap_red, p_colormap_green, p_colormap_blue,
            p_colormap_red_defaulted, p_colormap_green_defaulted, p_colormap_blue_defaulted
        )
    finally:
        tiff.close()


def test_set_get_field_lowlevel_colormap(colormap_test_data):
    ltc = lt.libtiff
    (
        tiff,
        colormap_red, colormap_green, colormap_blue,
        p_colormap_red, p_colormap_green, p_colormap_blue,
        p_colormap_red_defaulted, p_colormap_green_defaulted, p_colormap_blue_defaulted
    ) = colormap_test_data

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_COLORMAP, colormap_red, colormap_green, colormap_blue)
    assert ltc.TIFFGetField(
        tiff, lt.TIFFTAG_COLORMAP,
        ctypes.byref(p_colormap_red),
        ctypes.byref(p_colormap_green),
        ctypes.byref(p_colormap_blue)
    )
    assert ltc.TIFFGetFieldDefaulted(
        tiff, lt.TIFFTAG_COLORMAP,
        ctypes.byref(p_colormap_red_defaulted),
        ctypes.byref(p_colormap_green_defaulted),
        ctypes.byref(p_colormap_blue_defaulted)
    )

    for i in range(256):
        assert p_colormap_red[i] == i
        assert p_colormap_green[i] == i
        assert p_colormap_blue[i] == i

        assert p_colormap_red_defaulted[i] == i
        assert p_colormap_green_defaulted[i] == i
        assert p_colormap_blue_defaulted[i] == i


@pytest.mark.parametrize("type_name", TAG_TEST_DATA_BASE.keys())
def test_set_get_field(tmp_path, type_name, tag_test_data):
    tiff = lt.TIFF.open(tmp_path / f'libtiff_set_get_field_{type_name}.tiff', mode='w')
    try:
        test_data = tag_test_data[type_name]
        for _tag_const, tag_name, value, _default_value in test_data['values']:
            tiff.SetField(tag_name, value)
            assert tiff.GetField(tag_name) == value
    finally:
        tiff.close()


def test_set_get_field_colormap(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_set_get_field_colormap.tiff', mode='w')
    try:
        tiff.SetField('BitsPerSample', 8)
        # Test tags with count > 1
        colormap_red = list(range(256))
        colormap_green = list(range(256))
        colormap_blue = list(range(256))
        tiff.SetField('ColorMap', [colormap_red, colormap_green, colormap_blue])
        p_colormap_red, p_colormap_green, p_colormap_blue = tiff.GetField('ColorMap')

        # Check that the retrieved values are correct
        for i in range(256):
            assert p_colormap_red[i] == i
            assert p_colormap_green[i] == i
            assert p_colormap_blue[i] == i
    finally:
        tiff.close()


@pytest.mark.xfail(strict=True, reason="add_tags does not keep the TIFFExtender alive; later opens segfault")
def test_add_tags_keeps_extender_alive(tmp_path):
    # Run in a subprocess: when the extender is garbage collected, the next
    # TIFFOpen calls a freed callback and crashes the interpreter.
    script = """
import gc
import sys
import numpy as np
import libtiff.libtiff_ctypes as lt

lt.add_tags([lt.TIFFFieldInfo(40200, 1, 1, lt.TIFFDataType.TIFF_SHORT, lt.FIELD_CUSTOM,
                              True, False, b"LibtiffTestRegistry")])
gc.collect()
fn = sys.argv[1]
tiff = lt.TIFF.open(fn, mode='w')
tiff.SetField('LibtiffTestRegistry', 42)
tiff.write_image(np.zeros((2, 2), np.uint8))
tiff.close()
tiff = lt.TIFF.open(fn)
assert tiff.GetField('LibtiffTestRegistry') == 42
tiff.close()
"""
    proc = subprocess.run([sys.executable, '-c', script, str(tmp_path / 'registry.tif')],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.xfail(strict=True, reason="TIFF3D.read_image computes a float itemsize (bits / 8)")
def test_tiff3d_read_image(tmp_path):
    itype = np.uint32
    image = np.array([[[1, 2, 3], [4, 5, 6]]], itype)
    fn = str(tmp_path / "issue69.tif")
    tif = TIFFimage(image)
    tif.write_file(fn)
    del tif
    tif = lt.TIFF3D.open(fn)
    arr = tif.read_image()
    tif.close()
    np.testing.assert_array_equal(arr, image)
    assert arr.dtype == itype


@pytest.mark.xfail(strict=True, reason="TIFF3D.read_image computes a float itemsize (bits / 8)")
def test_tiff3d_read_image_multipage(tmp_path):
    fn = tmp_path / "tiff3d.tif"
    arr = np.arange(3 * 20 * 7, dtype=np.uint16).reshape(3, 20, 7)
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr)
    tiff.close()

    tiff = lt.TIFF3D.open(fn)
    arr2 = tiff.read_image()
    assert tiff.CurrentDirectory() == 0
    tiff.close()
    np.testing.assert_array_equal(arr, arr2)


@pytest.mark.xfail(strict=True, reason="GetField('PixelSizeX') eval()s text from ImageDescription")
@pytest.mark.parametrize(
    "descr",
    [
        b"PixelSizeX __import__('os').environ.__setitem__('PYLIBTIFF_PWNED','1')",
        b"PixelSizeX",
        b"PixelSizeX abc",
    ]
)
def test_pixelsize_does_not_eval(tmp_path, descr):
    fn = tmp_path / "pixelsize.tif"
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.SetField('ImageDescription', descr)
    tiff.write_image(np.zeros((2, 2), np.uint8))
    tiff.close()

    try:
        tiff = lt.TIFF.open(fn)
        assert tiff.GetField('PixelSizeX') is None
        tiff.info()
        tiff.close()
        assert os.environ.get('PYLIBTIFF_PWNED') is None
    finally:
        os.environ.pop('PYLIBTIFF_PWNED', None)


def test_pixelsize_from_description(tmp_path):
    fn = tmp_path / "pixelsize.tif"
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.SetField('ImageDescription', b"PixelSizeX 0.5\nPixelSizeY 2 RelativeTime 1e-3")
    tiff.write_image(np.zeros((2, 2), np.uint8))
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.GetField('PixelSizeX') == 0.5
    assert tiff.GetField('PixelSizeY') == 2.0
    assert tiff.GetField('RelativeTime') == 1e-3
    tiff.close()


@pytest.mark.xfail(strict=True, reason="SetField of pointer tags uses collections.Iterable (removed in Python 3.10) "
                                       "and passes a list to a scalar ctypes type")
def test_set_field_pointer_tag(tmp_path, monkeypatch):
    tag = 40300
    extenders.append(lt.add_tags([
        lt.TIFFFieldInfo(tag, 3, 3, lt.TIFFDataType.TIFF_LONG, lt.FIELD_CUSTOM,
                         True, False, b"LibtiffTestPointer"),
    ]))
    # A fixed count array tag without passcount is passed as a uint32* by libtiff
    monkeypatch.setitem(lt.tifftags, tag, (ctypes.POINTER(ctypes.c_uint32), lambda d: d[:3]))

    fn = tmp_path / "pointer_tag.tif"
    tiff = lt.TIFF.open(fn, mode='w')
    assert tiff.SetField(tag, [7, 8, 9]) == 1
    tiff.write_image(np.zeros((2, 2), np.uint8))
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.GetField(tag) == [7, 8, 9]
    tiff.close()


@pytest.mark.xfail(strict=True, reason="Strip/tile offsets and bytecounts are read as a single uint32")
def test_strip_offsets_are_full_arrays(tmp_path):
    fn = tmp_path / "tiles.tif"
    arr = np.arange(64 * 48, dtype=np.uint16).reshape(64, 48)
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_tiles(arr, 16, 16)
    tiff.close()

    n_tiles = 4 * 3
    tiff = lt.TIFF.open(fn)
    offsets = tiff.GetField('TileOffsets')
    bytecounts = tiff.GetField('TileByteCounts')
    tiff.close()
    assert len(offsets) == n_tiles
    assert all(isinstance(o, int) for o in offsets)
    assert bytecounts == [16 * 16 * 2] * n_tiles
    assert sorted(set(offsets)) == offsets


def _write_bigtiff_with_large_strip_offset(fn, offset):
    """Write a 1x1 BigTIFF whose (fake) strip offset does not fit 32 bits."""
    entries = [
        (256, 3, 1, 1),  # ImageWidth
        (257, 3, 1, 1),  # ImageLength
        (258, 3, 1, 8),  # BitsPerSample
        (259, 3, 1, 1),  # Compression
        (262, 3, 1, 1),  # Photometric
        (273, 16, 1, offset),  # StripOffsets (LONG8)
        (277, 3, 1, 1),  # SamplesPerPixel
        (278, 3, 1, 1),  # RowsPerStrip
        (279, 16, 1, 1),  # StripByteCounts (LONG8)
    ]
    ifd = struct.pack('<Q', len(entries))
    for tag, typ, count, value in entries:
        ifd += struct.pack('<HHQQ', tag, typ, count, value)
    ifd += struct.pack('<Q', 0)
    with open(fn, 'wb') as f:
        f.write(b'II+\x00' + struct.pack('<HHQ', 8, 0, 16) + ifd)


@pytest.mark.xfail(strict=True, reason="Strip/tile offsets and bytecounts are read as a single uint32")
def test_strip_offsets_64bit(tmp_path):
    fn = tmp_path / "bigtiff.tif"
    offset = 2 ** 33 + 16
    _write_bigtiff_with_large_strip_offset(fn, offset)
    tiff = lt.TIFF.open(fn)
    assert tiff.GetField('StripOffsets') == [offset]
    assert tiff.GetField('StripByteCounts') == [1]
    tiff.close()


def _write_lsm_like_tiff(fn, lsminfo):
    """Write a 1x1 TIFF with a CZ_LSMInfo (BYTE) tag, as found in LSM files."""
    n = 10
    data_off = 8 + 2 + n * 12 + 4
    lsm_off = data_off + 4
    entries = [
        (256, 3, 1, 1), (257, 3, 1, 1), (258, 3, 1, 8), (259, 3, 1, 1),
        (262, 3, 1, 1), (273, 4, 1, data_off), (277, 3, 1, 1), (278, 3, 1, 1),
        (279, 4, 1, 1), (lt.TIFFTAG_CZ_LSMINFO, 1, len(lsminfo), lsm_off),
    ]
    ifd = struct.pack('<H', n)
    for tag, typ, count, value in entries:
        ifd += struct.pack('<HHII', tag, typ, count, value)
    ifd += struct.pack('<I', 0)
    with open(fn, 'wb') as f:
        f.write(b'II*\x00' + struct.pack('<I', 8) + ifd + b'\x07\x00\x00\x00' + lsminfo)


@pytest.mark.skip(reason="Crashes on current code: GetField('CZ_LSMInfo') reads the tag with the wrong "
                         "type (c_toff_t is int32) and CZ_LSMInfo closes libtiff's file descriptor")
def test_cz_lsminfo(tmp_path):
    fn = tmp_path / "lsm_like.tif"
    lsminfo = struct.pack('<ii', 0x0400494C, 500) + bytes(492)
    _write_lsm_like_tiff(fn, lsminfo)
    tiff = lt.TIFF.open(fn)
    assert tiff.GetField('CZ_LSMInfo') == lsminfo
    assert 'magic_number=%d' % 0x0400494C in tiff.info()
    # libtiff's file descriptor must still be usable
    np.testing.assert_array_equal(tiff.read_image(), [[7]])
    tiff.close()


@pytest.mark.xfail(strict=True, reason="TIFF.copy skips the first directory and drops the last one")
def test_copy_multipage(tmp_path):
    arr = np.arange(3 * 5 * 6, dtype=np.uint16).reshape(3, 5, 6)
    tiff = lt.TIFF.open(tmp_path / 'multipage.tiff', mode='w')
    tiff.write_image(arr)
    tiff.close()

    tiff = lt.TIFF.open(tmp_path / 'multipage.tiff')
    tiff.copy(tmp_path / 'multipage_copy.tiff', compression='lzw')
    tiff.close()

    tiff = lt.TIFF.open(tmp_path / 'multipage_copy.tiff')
    pages = list(tiff.iter_images())
    assert tiff.GetField('Compression') == lt.COMPRESSION_LZW
    tiff.close()
    assert len(pages) == 3
    np.testing.assert_array_equal(np.array(pages), arr)


@pytest.mark.xfail(strict=True, reason="TIFF.copy checks tag names with assert instead of raising ValueError")
def test_copy_unknown_tag(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'image.tiff', mode='w')
    tiff.write_image(np.zeros((2, 2), np.uint8))
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'image.tiff')
    with pytest.raises(ValueError):
        tiff.copy(tmp_path / 'image_copy.tiff', notatag=1)
    tiff.close()


_XFAIL_TAG_DEFINE = pytest.mark.xfail(
    strict=True, reason="get_tag_define uses str.title() and a single split, so most names raise KeyError")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("compression", lt.TIFFTAG_COMPRESSION),
        ("imagedescription", lt.TIFFTAG_IMAGEDESCRIPTION),
        pytest.param("tifftag_artist", lt.TIFFTAG_ARTIST, marks=_XFAIL_TAG_DEFINE),
        pytest.param("cz_lsminfo", lt.TIFFTAG_CZ_LSMINFO, marks=_XFAIL_TAG_DEFINE),
        pytest.param("photometric_rgb", lt.PHOTOMETRIC_RGB, marks=_XFAIL_TAG_DEFINE),
        pytest.param("PLANARCONFIG_CONTIG", lt.PLANARCONFIG_CONTIG, marks=_XFAIL_TAG_DEFINE),
        pytest.param("compression_adobe_deflate", lt.COMPRESSION_ADOBE_DEFLATE, marks=_XFAIL_TAG_DEFINE),
        pytest.param("sampleformat_ieeefp", lt.SAMPLEFORMAT_IEEEFP, marks=_XFAIL_TAG_DEFINE),
        ("notatag", None),
    ]
)
def test_get_tag_define(name, expected):
    assert lt.TIFF.get_tag_define(name) == expected


_XFAIL_BYTESWAP = pytest.mark.xfail(
    strict=True, reason="write_image/write_tiles write non-native byte order arrays without byteswapping")


@pytest.mark.parametrize("byteorder", ['<', pytest.param('>', marks=_XFAIL_BYTESWAP)])
@pytest.mark.parametrize("dtype", ['u2', 'i4', 'f8'])
def test_write_image_byteswapped(tmp_path, byteorder, dtype):
    arr = np.arange(5 * 6).reshape(5, 6).astype(byteorder + dtype)
    fn = tmp_path / 'byteswapped.tiff'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr)
    tiff.close()
    tiff = lt.TIFF.open(fn)
    arr2 = tiff.read_image()
    tiff.close()
    np.testing.assert_array_equal(arr2, arr)


@pytest.mark.parametrize("byteorder", ['<', pytest.param('>', marks=_XFAIL_BYTESWAP)])
def test_write_tiles_byteswapped(tmp_path, byteorder):
    arr = np.arange(40 * 24).reshape(40, 24).astype(byteorder + 'u2')
    fn = tmp_path / 'byteswapped_tiles.tiff'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_tiles(arr, 16, 16)
    tiff.close()
    tiff = lt.TIFF.open(fn)
    arr2 = tiff.read_image()
    tiff.close()
    np.testing.assert_array_equal(arr2, arr)


@pytest.mark.xfail(strict=True, reason="write_image writes a 1-D array as a single column instead of a single row")
def test_write_1d(tmp_path):
    arr = np.arange(20, dtype=np.uint8)
    tiff = lt.TIFF.open(tmp_path / 'strips_1d.tiff', mode='w')
    tiff.write_image(arr)
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'strips_1d.tiff')
    np.testing.assert_array_equal(tiff.read_image(), arr[np.newaxis, :])
    tiff.close()

    tiff = lt.TIFF.open(tmp_path / 'tiles_1d.tiff', mode='w')
    assert tiff.write_tiles(arr, 16, 16) == 16 * 16 * 2
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'tiles_1d.tiff')
    np.testing.assert_array_equal(tiff.read_image(), arr[np.newaxis, :])
    tiff.close()


@pytest.mark.xfail(strict=True, reason="ReadTile returns a ctypes object instead of an int")
def test_read_tile_errors(tmp_path):
    arr = np.arange(32 * 32, dtype=np.uint16).reshape(32, 32)
    tiff = lt.TIFF.open(tmp_path / 'tiles.tiff', mode='w')
    tiff.write_tiles(arr, 16, 16)
    tiff.close()

    tiff = lt.TIFF.open(tmp_path / 'tiles.tiff')
    buf = np.zeros((16, 16), np.uint16)
    assert tiff.ReadTile(buf.ctypes.data, 16, 0, 0, 0) == buf.nbytes
    np.testing.assert_array_equal(buf, arr[:16, 16:])
    lt.suppress_errors()
    try:
        assert tiff.ReadTile(buf.ctypes.data, 1000, 0, 0, 0) == -1
    finally:
        lt.libtiff.TIFFSetErrorHandler(lt.TIFFErrorHandler())
    tiff.close()


@pytest.mark.xfail(strict=True, reason="TIFFReadEncodedTile is declared with the wrong argtypes and restype")
def test_read_encoded_tile(tmp_path):
    arr = np.arange(32 * 32, dtype=np.uint16).reshape(32, 32)
    tiff = lt.TIFF.open(tmp_path / 'tiles.tiff', mode='w')
    tiff.write_tiles(arr, 16, 16)
    tiff.close()

    tiff = lt.TIFF.open(tmp_path / 'tiles.tiff')
    buf = np.zeros((16, 16), np.uint16)
    size = lt.libtiff.TIFFReadEncodedTile(tiff, 1, buf.ctypes.data, buf.nbytes).value
    tiff.close()
    assert size == buf.nbytes
    np.testing.assert_array_equal(buf, arr[:16, 16:])


@pytest.mark.xfail(strict=True, reason="TIFFDefaultTileSize is declared with uint32 args instead of uint32 pointers")
def test_default_tile_size(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'tiles.tiff', mode='w')
    width = ctypes.c_uint32(0)
    height = ctypes.c_uint32(0)
    lt.libtiff.TIFFDefaultTileSize(tiff, ctypes.byref(width), ctypes.byref(height))
    tiff.close()
    assert width.value > 0 and width.value % 16 == 0
    assert height.value > 0 and height.value % 16 == 0


@pytest.mark.xfail(strict=True, reason="CurrentDirectory/CurrentStrip/CurrentTile return ctypes objects")
def test_current_directory_is_int(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'multipage.tiff', mode='w')
    tiff.write_image(np.zeros((2, 2, 2), np.uint8))
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'multipage.tiff')
    tiff.ReadDirectory()
    assert tiff.CurrentDirectory() == 1
    assert isinstance(tiff.CurrentStrip(), int)
    assert isinstance(tiff.CurrentTile(), int)
    tiff.close()


def test_open_missing_file(tmp_path):
    lt.suppress_errors()
    try:
        with pytest.raises(TypeError, match='Failed to open file'):
            lt.TIFF.open(tmp_path / 'does_not_exist.tif')
    finally:
        lt.libtiff.TIFFSetErrorHandler(lt.TIFFErrorHandler())


@pytest.mark.parametrize("compression", [None, 'lzw', 'deflate', 'packbits'])
@pytest.mark.parametrize("dtype", ['u1', 'u2', 'u4', 'u8', 'i1', 'i2', 'i4', 'i8', 'f4', 'f8', 'c8', 'c16'])
def test_write_read_image_dtypes(tmp_path, dtype, compression):
    arr = (np.arange(7 * 9).reshape(7, 9) - 20).astype(dtype)
    fn = tmp_path / 'dtypes.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr, compression=compression)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    arr2 = tiff.read_image()
    assert tiff.GetField('BitsPerSample') == arr.dtype.itemsize * 8
    assert tiff.GetField('Compression') == lt.TIFF._fix_compression(compression)
    tiff.close()
    assert arr2.dtype == arr.dtype
    np.testing.assert_array_equal(arr2, arr)


def test_write_image_bool(tmp_path):
    arr = np.arange(12).reshape(3, 4) % 3 == 0
    tiff = lt.TIFF.open(tmp_path / 'bool.tif', mode='w')
    tiff.write_image(arr)
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'bool.tif')
    arr2 = tiff.read_image()
    tiff.close()
    assert arr2.dtype == np.uint8
    np.testing.assert_array_equal(arr2, arr)


def test_write_image_unsupported(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'unsupported.tif', mode='w')
    with pytest.raises(NotImplementedError):
        tiff.write_image(np.array([['a']]))
    with pytest.raises(NotImplementedError):
        tiff.write_image(np.zeros((2, 2, 2, 2), np.uint8))
    with pytest.raises(NotImplementedError):
        tiff.write_image(np.zeros((2, 2), np.uint8), compression=1.5)
    tiff.close()


@pytest.mark.xfail(strict=True, reason="write_image only sets BitsPerSample, SampleFormat and Compression on "
                                       "the first page of a 3-D array")
def test_multipage_iter_images(tmp_path):
    arr = np.arange(4 * 5 * 6, dtype=np.uint16).reshape(4, 5, 6)
    fn = tmp_path / 'multipage.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert not tiff.IsTiled()
    assert tiff.GetField('ImageWidth') == 6
    assert tiff.GetField('ImageLength') == 5
    pages = list(tiff.iter_images())
    assert len(pages) == 4
    np.testing.assert_array_equal(np.array(pages), arr)
    # iter_images rewinds to the first directory
    np.testing.assert_array_equal(tiff.read_image(), arr[0])
    assert tiff.SetDirectory(2)
    np.testing.assert_array_equal(tiff.read_image(), arr[2])
    assert tiff.LastDirectory() == 0
    assert tiff.SetDirectory(3)
    assert tiff.LastDirectory() == 1
    tiff.close()


@pytest.mark.parametrize("depth", [3, 4])
def test_write_rgb_contig(tmp_path, depth):
    arr = np.arange(5 * 6 * depth, dtype=np.uint8).reshape(5, 6, depth)
    fn = tmp_path / 'rgb.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr, write_rgb=True)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.GetField('Photometric') == lt.PHOTOMETRIC_RGB
    assert tiff.GetField('PlanarConfig') == lt.PLANARCONFIG_CONTIG
    assert tiff.GetField('SamplesPerPixel') == depth
    np.testing.assert_array_equal(tiff.read_image(), arr)
    tiff.close()


@pytest.mark.parametrize("depth", [3, 5])
def test_write_rgb_separate(tmp_path, depth):
    arr = np.arange(depth * 5 * 6, dtype=np.uint16).reshape(depth, 5, 6)
    fn = tmp_path / 'rgb_separate.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr, write_rgb=True)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.GetField('Photometric') == lt.PHOTOMETRIC_RGB
    assert tiff.GetField('PlanarConfig') == lt.PLANARCONFIG_SEPARATE
    assert tiff.GetField('SamplesPerPixel') == depth
    assert tiff.NumberOfStrips() == depth
    np.testing.assert_array_equal(tiff.read_image(), arr)
    tiff.close()


def test_write_big_endian_file(tmp_path):
    arr = np.arange(5 * 6, dtype=np.uint16).reshape(5, 6) * 257
    fn = tmp_path / 'big_endian.tif'
    tiff = lt.TIFF.open(fn, mode='wb')
    tiff.write_image(arr)
    tiff.close()
    with open(fn, 'rb') as f:
        assert f.read(4) == b'MM\x00*'

    tiff = lt.TIFF.open(fn)
    assert tiff.IsByteSwapped() == (sys.byteorder == 'little')
    np.testing.assert_array_equal(tiff.read_image(), arr)
    tiff.close()


def test_strip_access(tmp_path):
    arr = np.arange(4 * 10, dtype=np.uint8).reshape(4, 10)
    fn = tmp_path / 'strips.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.GetMode() == os.O_RDONLY
    assert tiff.FileName() == os.fsencode(fn)
    assert tiff.NumberOfStrips() == 1
    assert tiff.StripSize() == arr.nbytes
    assert tiff.RawStripSize(0) == arr.nbytes
    assert tiff.ScanlineSize() == 10
    buf = np.zeros_like(arr)
    assert tiff.ReadRawStrip(0, buf.ctypes.data, buf.nbytes) == arr.nbytes
    np.testing.assert_array_equal(buf, arr)
    line = np.zeros(10, np.uint8)
    tiff.ReadScanline(line.ctypes.data, 2)
    np.testing.assert_array_equal(line, arr[2])
    tiff.close()


def test_info(tmp_path):
    fn = tmp_path / 'info.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.SetField('Artist', b'Some Body')
    tiff.write_image(np.zeros((5, 6), np.uint16), compression='lzw')
    tiff.close()

    tiff = lt.TIFF.open(fn)
    info = tiff.info().splitlines()
    tiff.close()
    assert info[0] == 'filename: %s' % os.fsencode(fn)
    assert "Artist: b'Some Body'" in info
    assert 'ImageWidth: 6' in info
    assert 'ImageLength: 5' in info
    assert 'BitsPerSample: 16' in info
    assert 'Compression: COMPRESSION_LZW' in info
    assert 'PhotoMetric: PHOTOMETRIC_MINISBLACK' in info
    assert 'Predictor: 2' in info


@pytest.mark.parametrize(
    ("value", "name"),
    [
        (lt.TIFFTAG_IMAGEWIDTH, 'TIFFTAG_IMAGEWIDTH'),
        (lt.TIFFTAG_ARTIST, 'TIFFTAG_ARTIST'),
        (123456, None),
    ]
)
def test_get_tag_name(value, name):
    assert lt.TIFF.get_tag_name(value) == name


@pytest.mark.parametrize(
    ("bits", "sample_format", "dtype"),
    [
        (8, None, np.uint8),
        (16, lt.SAMPLEFORMAT_UINT, np.uint16),
        (32, lt.SAMPLEFORMAT_INT, np.int32),
        (64, lt.SAMPLEFORMAT_IEEEFP, np.float64),
        (128, lt.SAMPLEFORMAT_COMPLEXIEEEFP, np.complex128),
    ]
)
def test_get_numpy_type(bits, sample_format, dtype):
    assert lt.TIFF.get_numpy_type(bits, sample_format) is dtype


@pytest.mark.parametrize(("bits", "sample_format"), [(12, None), (8, lt.SAMPLEFORMAT_VOID)])
def test_get_numpy_type_unsupported(bits, sample_format):
    with pytest.raises(NotImplementedError):
        lt.TIFF.get_numpy_type(bits, sample_format)


def test_tiff3d_open_and_read_2d(tmp_path):
    arr = np.arange(3 * 5 * 6, dtype=np.uint8).reshape(3, 5, 6)
    fn = tmp_path / 'tiff3d.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_image(arr)
    tiff.close()

    tiff = lt.TIFF3D.open(fn)
    assert isinstance(tiff, lt.TIFF3D)
    np.testing.assert_array_equal(tiff.read_image(as3d=False), arr[0])
    tiff.close()
    # TIFF3D.open must not change what TIFF.open returns
    tiff = lt.TIFF.open(fn)
    assert type(tiff) is lt.TIFF
    tiff.close()


@pytest.mark.parametrize("planar", ['contig', 'separate'])
def test_write_read_tiles_rgb(tmp_path, planar):
    if planar == 'contig':
        arr = np.arange(40 * 24 * 3, dtype=np.uint16).reshape(40, 24, 3)
    else:
        arr = np.arange(3 * 40 * 24, dtype=np.uint16).reshape(3, 40, 24)
    fn = tmp_path / 'tiles_rgb.tif'
    tiff = lt.TIFF.open(fn, mode='w')
    tiff.write_tiles(arr, 16, 16, compression='lzw', write_rgb=True)
    tiff.close()

    tiff = lt.TIFF.open(fn)
    assert tiff.IsTiled()
    assert tiff.GetField('TileWidth') == 16
    assert tiff.GetField('TileLength') == 16
    np.testing.assert_array_equal(tiff.read_image(), arr)
    np.testing.assert_array_equal(tiff.read_tiles(np.uint16), arr)
    tiff.close()


def test_read_tiles_not_tiled(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'strips.tif', mode='w')
    tiff.write_image(np.zeros((4, 4), np.uint8))
    tiff.close()
    tiff = lt.TIFF.open(tmp_path / 'strips.tif')
    with pytest.raises(ValueError, match='TILEWIDTH'):
        tiff.read_tiles()
    with pytest.raises(ValueError, match='TILEWIDTH'):
        tiff.read_one_tile(0, 0)
    tiff.close()

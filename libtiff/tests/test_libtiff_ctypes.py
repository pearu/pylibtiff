import ctypes
import numpy as np
import pytest
import time
from libtiff import TIFFimage

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
    tiff.SetField('ImageDescription', b'Hey\nyou\x00')
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
                tiff.copy(tmp_path / 'libtiff_test_copy2.tiff',
                          compression=compression,
                          imagedescription=b'hoo\x00',
                          sampleformat=sampleformat,
                          bitspersample=bitspersample)
                tiff2 = lt.TIFF.open(tmp_path / 'libtiff_test_copy2.tiff', mode='r')
                arr3 = tiff2.read_image()
                assert (arr == arr3).all(), 'arrays not equal %r' % (
                    (compression, sampleformat, bitspersample),)
    print('test copy ok')


def test_set_get_field_lowlevel(tmp_path):
    ltc = lt.libtiff
    tiff = lt.TIFF.open(tmp_path / 'libtiff_set_get_field_lowlevel.tiff', mode='w')

    # Store the output of TIFFGetField
    uint16_data = ctypes.c_uint16(0)
    p_uint16_data = ctypes.byref(uint16_data)
    uint32_data = ctypes.c_uint32(0)
    p_uint32_data = ctypes.byref(uint32_data)
    float_data = ctypes.c_float(0.0)
    p_float_data = ctypes.byref(float_data)
    double_data = ctypes.c_double(0.0)
    p_double_data = ctypes.byref(double_data)
    char_p_data = ctypes.c_char_p(b'')
    p_char_p_data = ctypes.byref(char_p_data)

    # Store the output of TIFFGetFieldDefaulted
    uint16_data_defaulted = ctypes.c_uint16(0)
    p_uint16_data_defaulted = ctypes.byref(uint16_data_defaulted)
    uint32_data_defaulted = ctypes.c_uint32(0)
    p_uint32_data_defaulted = ctypes.byref(uint32_data_defaulted)
    float_data_defaulted = ctypes.c_float(0.0)
    p_float_data_defaulted = ctypes.byref(float_data_defaulted)
    double_data_defaulted = ctypes.c_double(0.0)
    p_double_data_defaulted = ctypes.byref(double_data_defaulted)
    char_p_data_defaulted = ctypes.c_char_p(b'')
    p_char_p_data_defaulted = ctypes.byref(char_p_data_defaulted)

    # Test uint16 tags
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SAMPLEFORMAT, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.SAMPLEFORMAT_UINT

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SAMPLEFORMAT, lt.SAMPLEFORMAT_INT)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SAMPLEFORMAT, p_uint16_data)
    assert uint16_data.value == lt.SAMPLEFORMAT_INT
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SAMPLEFORMAT, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.SAMPLEFORMAT_INT

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SAMPLEFORMAT, lt.SAMPLEFORMAT_UINT)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SAMPLEFORMAT, p_uint16_data)
    assert uint16_data.value == lt.SAMPLEFORMAT_UINT
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SAMPLEFORMAT, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.SAMPLEFORMAT_UINT

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_COMPRESSION, lt.COMPRESSION_LZW)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_COMPRESSION, p_uint16_data)
    assert uint16_data.value == lt.COMPRESSION_LZW
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_COMPRESSION, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.COMPRESSION_LZW

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_ORIENTATION, lt.ORIENTATION_TOPLEFT)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_ORIENTATION, p_uint16_data)
    assert uint16_data.value == lt.ORIENTATION_TOPLEFT
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_ORIENTATION, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.ORIENTATION_TOPLEFT

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_THRESHHOLDING, lt.THRESHHOLD_BILEVEL)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_THRESHHOLDING, p_uint16_data)
    assert uint16_data.value == lt.THRESHHOLD_BILEVEL
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_THRESHHOLDING, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.THRESHHOLD_BILEVEL

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_FILLORDER, lt.FILLORDER_MSB2LSB)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_FILLORDER, p_uint16_data)
    assert uint16_data.value == lt.FILLORDER_MSB2LSB
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_FILLORDER, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == lt.FILLORDER_MSB2LSB

    # Test uint32 tags
    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_IMAGEWIDTH, 256)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_IMAGEWIDTH, p_uint32_data)
    assert uint32_data.value == 256
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_IMAGEWIDTH, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == 256

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_IMAGELENGTH, 256)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_IMAGELENGTH, p_uint32_data)
    assert uint32_data.value == 256
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_IMAGELENGTH, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == 256

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SUBFILETYPE, lt.FILETYPE_REDUCEDIMAGE)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SUBFILETYPE, p_uint32_data)
    assert uint32_data.value == lt.FILETYPE_REDUCEDIMAGE
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SUBFILETYPE, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == lt.FILETYPE_REDUCEDIMAGE

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_TILEWIDTH, 256)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_TILEWIDTH, p_uint32_data)
    assert uint32_data.value == 256
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_TILEWIDTH, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == 256

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_TILELENGTH, 256)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_TILELENGTH, p_uint32_data)
    assert uint32_data.value == 256
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_TILELENGTH, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == 256

    # Test float tags
    # NOTE: some tags are defined as float but can be set as float or double
    # Using ctypes.c_float instead of ctypes.c_double results in
    #       "RuntimeError: ffi_prep_cif_var failed"
    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_XRESOLUTION, ctypes.c_double(88.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_XRESOLUTION, p_float_data)
    assert float_data.value == 88.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_XRESOLUTION, p_float_data_defaulted)
    assert float_data_defaulted.value == 88.0

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_YRESOLUTION, ctypes.c_double(88.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_YRESOLUTION, p_float_data)
    assert float_data.value == 88.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_YRESOLUTION, p_float_data_defaulted)
    assert float_data_defaulted.value == 88.0

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_XPOSITION, ctypes.c_double(88.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_XPOSITION, p_float_data)
    assert float_data.value == 88.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_XPOSITION, p_float_data_defaulted)
    assert float_data_defaulted.value == 88.0

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_YPOSITION, ctypes.c_double(88.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_YPOSITION, p_float_data)
    assert float_data.value == 88.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_YPOSITION, p_float_data_defaulted)
    assert float_data_defaulted.value == 88.0

    # Test double tags
    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SMAXSAMPLEVALUE, ctypes.c_double(255.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SMAXSAMPLEVALUE, p_double_data)
    assert double_data.value == 255.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SMAXSAMPLEVALUE, p_double_data_defaulted)
    assert double_data_defaulted.value == 255.0

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SMINSAMPLEVALUE, ctypes.c_double(0.0))
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SMINSAMPLEVALUE, p_double_data)
    assert double_data.value == 0.0
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SMINSAMPLEVALUE, p_double_data_defaulted)
    assert double_data_defaulted.value == 0.0

    # Test string tags
    test_string = b"test string"
    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_ARTIST, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_ARTIST, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_ARTIST, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_DATETIME, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_DATETIME, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_DATETIME, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_HOSTCOMPUTER, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_HOSTCOMPUTER, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_HOSTCOMPUTER, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_IMAGEDESCRIPTION, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_IMAGEDESCRIPTION, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_IMAGEDESCRIPTION, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_MAKE, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_MAKE, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_MAKE, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_MODEL, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_MODEL, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_MODEL, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_SOFTWARE, test_string)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_SOFTWARE, p_char_p_data)
    assert char_p_data.value == test_string
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_SOFTWARE, p_char_p_data_defaulted)
    assert char_p_data_defaulted.value == test_string

    # Test setting a tag with a different data type
    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_IMAGEWIDTH, 128)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_IMAGEWIDTH, p_uint32_data)
    assert uint32_data.value == 128
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_IMAGEWIDTH, p_uint32_data_defaulted)
    assert uint32_data_defaulted.value == 128

    assert ltc.TIFFSetField(tiff, lt.TIFFTAG_BITSPERSAMPLE, 8)
    assert ltc.TIFFGetField(tiff, lt.TIFFTAG_BITSPERSAMPLE, p_uint16_data)
    assert uint16_data.value == 8
    assert ltc.TIFFGetFieldDefaulted(tiff, lt.TIFFTAG_BITSPERSAMPLE, p_uint16_data_defaulted)
    assert uint16_data_defaulted.value == 8

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

    # Check that the retrieved values are correct
    for i in range(256):
        assert p_colormap_red[i] == i
        assert p_colormap_green[i] == i
        assert p_colormap_blue[i] == i

        assert p_colormap_red_defaulted[i] == i
        assert p_colormap_green_defaulted[i] == i
        assert p_colormap_blue_defaulted[i] == i

    tiff.close()


def test_set_get_field(tmp_path):
    tiff = lt.TIFF.open(tmp_path / 'libtiff_set_get_field_lowlevel.tiff', mode='w')

    # Test uint16 tags
    tiff.SetField('SampleFormat', lt.SAMPLEFORMAT_INT)
    assert tiff.GetField('SampleFormat') == lt.SAMPLEFORMAT_INT

    tiff.SetField('Compression', lt.COMPRESSION_LZW)
    assert tiff.GetField('Compression') == lt.COMPRESSION_LZW

    tiff.SetField('Orientation', lt.ORIENTATION_TOPLEFT)
    assert tiff.GetField('Orientation') == lt.ORIENTATION_TOPLEFT

    tiff.SetField('Threshholding', lt.THRESHHOLD_BILEVEL)
    assert tiff.GetField('Threshholding') == lt.THRESHHOLD_BILEVEL

    tiff.SetField('FillOrder', lt.FILLORDER_MSB2LSB)
    assert tiff.GetField('FillOrder') == lt.FILLORDER_MSB2LSB

    # Test uint32 tags
    tiff.SetField('ImageWidth', 256)
    assert tiff.GetField('ImageWidth') == 256

    tiff.SetField('ImageLength', 256)
    assert tiff.GetField('ImageLength') == 256

    tiff.SetField('SubfileType', lt.FILETYPE_REDUCEDIMAGE)
    assert tiff.GetField('SubfileType') == lt.FILETYPE_REDUCEDIMAGE

    tiff.SetField('TileWidth', 256)
    assert tiff.GetField('TileWidth') == 256

    tiff.SetField('TileLength', 256)
    assert tiff.GetField('TileLength') == 256

    # Test float tags
    tiff.SetField('XResolution', 88.0)
    assert tiff.GetField('XResolution') == 88.0

    tiff.SetField('YResolution', 88.0)
    assert tiff.GetField('YResolution') == 88.0

    tiff.SetField('XPosition', 88.0)
    assert tiff.GetField('XPosition') == 88.0

    tiff.SetField('YPosition', 88.0)
    assert tiff.GetField('YPosition') == 88.0

    # Test double tags
    tiff.SetField('SMaxSampleValue', 255.0)
    assert tiff.GetField('SMaxSampleValue') == 255.0

    tiff.SetField('SMinSampleValue', 0.0)
    assert tiff.GetField('SMinSampleValue') == 0.0

    # Test string tags
    test_string = b"test string"
    tiff.SetField('Artist', test_string)
    assert tiff.GetField('Artist') == test_string

    tiff.SetField('DateTime', test_string)
    assert tiff.GetField('DateTime') == test_string

    tiff.SetField('HostComputer', test_string)
    assert tiff.GetField('HostComputer') == test_string

    tiff.SetField('ImageDescription', test_string)
    assert tiff.GetField('ImageDescription') == test_string

    tiff.SetField('Make', test_string)
    assert tiff.GetField('Make') == test_string

    tiff.SetField('Model', test_string)
    assert tiff.GetField('Model') == test_string

    tiff.SetField('Software', test_string)
    assert tiff.GetField('Software') == test_string

    # Test setting a tag with a different data type
    tiff.SetField('ImageWidth', 128)
    assert tiff.GetField('ImageWidth') == 128

    tiff.SetField('BitsPerSample', 8)
    assert tiff.GetField('BitsPerSample') == 8

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

    tiff.close()

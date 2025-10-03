import ctypes
from libtiff import libtiff_ctypes as lt
import tempfile
import pathlib
import pprint

tag_test_data = {
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


def get_default_tag_values(tmp_path):
    ltc = lt.libtiff
    tiff = lt.TIFF.open(tmp_path / 'default_values.tiff', mode='w')
    defaults = {}

    data_holders = {
        'uint16': ctypes.c_uint16(0),
        'uint32': ctypes.c_uint32(0),
        'float': ctypes.c_float(0.0),
        'double': ctypes.c_double(0.0),
        'string': ctypes.c_char_p(b''),
    }

    for type_name, test_data in tag_test_data.items():
        for tag_const, _, _ in test_data['values']:
            if tag_const in defaults:
                continue  # Already checked

            data_holder = data_holders[type_name]
            p_data_holder = ctypes.byref(data_holder)

            if ltc.TIFFGetFieldDefaulted(tiff, tag_const, p_data_holder):
                defaults[tag_const] = data_holder.value
            else:
                defaults[tag_const] = None
    tiff.close()
    # manually add missing default
    defaults[lt.TIFFTAG_SAMPLEFORMAT] = 1
    return defaults


with tempfile.TemporaryDirectory() as tmpdir:
    default_values = get_default_tag_values(pathlib.Path(tmpdir))

    new_tag_test_data = {}
    for type_name, test_data in tag_test_data.items():
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

    print("tag_test_data = " + pprint.pformat(new_tag_test_data))

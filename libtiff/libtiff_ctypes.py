#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

Homepage:  http://pylibtiff.googlecode.com/
"""
from __future__ import print_function
import os
import sys
import numpy as np
# from numpy import ctypeslib
import ctypes
import ctypes.util
import struct
import collections

__author__ = 'Pearu Peterson'
__date__ = 'April 2009'
__license__ = 'BSD'
__version__ = '0.3-svn'
__all__ = ['libtiff', 'TIFF']

if os.name == 'nt':
    # assume that the directory of libtiff3.dll is in PATH.
    lib = ctypes.util.find_library('libtiff3')
    if lib is None:
        lib = ctypes.util.find_library('libtiff.dll')
    if lib is None:
        # try default installation path:
        lib = r'C:\Program Files\GnuWin32\bin\libtiff3.dll'
        if os.path.isfile(lib):
            print('You should add %r to PATH environment variable and '
                  'reboot.' % (os.path.dirname(lib)))
        else:
            lib = None
else:
    if hasattr(sys, 'frozen') and sys.platform == 'darwin' and \
            os.path.exists('../Frameworks/libtiff.dylib'):
        # py2app support, see Issue 8.
        lib = '../Frameworks/libtiff.dylib'
    else:
        lib = ctypes.util.find_library('tiff')
if lib is None:
    raise ImportError('Failed to find TIFF library. Make sure that libtiff '
                      'is installed and its location is listed in '
                      'PATH|LD_LIBRARY_PATH|..')

libtiff = ctypes.cdll.LoadLibrary(lib)

libtiff.TIFFGetVersion.restype = ctypes.c_char_p
libtiff.TIFFGetVersion.argtypes = []

libtiff_version_str = libtiff.TIFFGetVersion()
i = libtiff_version_str.lower().split().index(b'version')
assert i != -1, repr(libtiff_version_str.decode())
libtiff_version = libtiff_version_str.split()[i + 1].decode()

tiff_h_name = 'tiff_h_%s' % (libtiff_version.replace('.', '_'))

try:
    exec(u"import libtiff.{0:s} as tiff_h".format(tiff_h_name))
    # the following for inspections
    from libtiff.tiff_h_4_0_6 import *
except ImportError:
    tiff_h = None

if tiff_h is None:
    include_tiff_h = os.path.join(os.path.split(lib)[0], '..', 'include',
                                  'tiff.h')
    if not os.path.isfile(include_tiff_h):
        include_tiff_h = os.path.join(os.path.split(lib)[0], 'include',
                                      'tiff.h')
    if not os.path.isfile(include_tiff_h):
        # fix me for windows:
        include_tiff_h = os.path.join('/usr', 'include', 'tiff.h')
        # print(include_tiff_h)
    if not os.path.isfile(include_tiff_h):
        import glob

        include_tiff_h = (glob.glob(os.path.join('/usr', 'include',
                                                 '*linux-gnu', 'tiff.h')) +
                          [include_tiff_h])[0]
    if not os.path.isfile(include_tiff_h):
        # Base it off of the python called
        include_tiff_h = os.path.realpath(os.path.join(os.path.split(
            sys.executable)[0], '..', 'include', 'tiff.h'))
    # print(include_tiff_h)
    if not os.path.isfile(include_tiff_h):
        raise ValueError('Failed to find TIFF header file (may be need to '
                         'run: sudo apt-get install libtiff4-dev)')
    # Read TIFFTAG_* constants for the header file:
    f = open(include_tiff_h, 'r')
    l = []
    d = {}
    for line in f.readlines():
        if not line.startswith('#define'):
            continue
        words = line[7:].lstrip().split()
        if len(words) > 2:
            words[1] = ''.join(words[1:])
            del words[2:]
        if len(words) != 2:
            continue
        name, value = words
        i = value.find('/*')
        if i != -1:
            value = value[:i]
        if value in d:
            value = d[value]
        else:
            try:
                value = eval(value)
            except:
                print(repr((value, line)))
                raise
        d[name] = value
        l.append('%s = %s' % (name, value))
    f.close()

    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      tiff_h_name + '.py')
    print('Generating %r' % fn)
    f = open(fn, 'w')
    f.write('\n'.join(l) + '\n')
    f.close()
else:
    d = tiff_h.__dict__

TIFFTAG_CZ_LSMINFO = 34412
d['TIFFTAG_CZ_LSMINFO'] = TIFFTAG_CZ_LSMINFO

define_to_name_map = dict(Orientation={}, Compression={},
                          PhotoMetric={}, PlanarConfig={},
                          SampleFormat={}, FillOrder={},
                          FaxMode={}, TiffTag={}
                          )

name_to_define_map = dict(Orientation={}, Compression={},
                          PhotoMetric={}, PlanarConfig={},
                          SampleFormat={}, FillOrder={},
                          FaxMode={}, TiffTag={}
                          )

for name, value in list(d.items()):
    if name.startswith('_'):
        continue
    globals()[name] = value
    for n in define_to_name_map:
        if name.startswith(n.upper()):
            define_to_name_map[n][value] = name
            name_to_define_map[n][name] = value


# types defined by tiff.h
class c_ttag_t(ctypes.c_uint):
    pass


class c_tdir_t(ctypes.c_uint16):
    pass


class c_tsample_t(ctypes.c_uint16):
    pass


class c_tstrip_t(ctypes.c_uint32):
    pass


class c_ttile_t(ctypes.c_uint32):
    pass


class c_tsize_t(ctypes.c_int32):
    pass


class c_toff_t(ctypes.c_int32):
    pass


class c_tdata_t(ctypes.c_void_p):
    pass


class c_thandle_t(ctypes.c_void_p):
    pass


# types defined for creating custom tags
FIELD_CUSTOM = 65


class TIFFDataType(object):
    """Place holder for the enum in C.

    typedef enum {
        TIFF_NOTYPE = 0,    /* placeholder */
        TIFF_BYTE   = 1,    /* 8-bit unsigned integer */
        TIFF_ASCII  = 2,    /* 8-bit bytes w/ last byte null */
        TIFF_SHORT  = 3,    /* 16-bit unsigned integer */
        TIFF_LONG   = 4,    /* 32-bit unsigned integer */
        TIFF_RATIONAL   = 5,    /* 64-bit unsigned fraction */
        TIFF_SBYTE  = 6,    /* !8-bit signed integer */
        TIFF_UNDEFINED  = 7,    /* !8-bit untyped data */
        TIFF_SSHORT = 8,    /* !16-bit signed integer */
        TIFF_SLONG  = 9,    /* !32-bit signed integer */
        TIFF_SRATIONAL  = 10,   /* !64-bit signed fraction */
        TIFF_FLOAT  = 11,   /* !32-bit IEEE floating point */
        TIFF_DOUBLE = 12,   /* !64-bit IEEE floating point */
        TIFF_IFD    = 13    /* %32-bit unsigned integer (offset) */
    } TIFFDataType;
    """
    ctype = ctypes.c_int
    TIFF_NOTYPE = 0
    TIFF_BYTE = 1
    TIFF_ASCII = 2
    TIFF_SHORT = 3
    TIFF_LONG = 4
    TIFF_RATIONAL = 5
    TIFF_SBYTE = 6
    TIFF_UNDEFINED = 7
    TIFF_SSHORT = 8
    TIFF_SLONG = 9
    TIFF_SRATIONAL = 10
    TIFF_FLOAT = 11
    TIFF_DOUBLE = 12
    TIFF_IFD = 13


ttype2ctype = {
    TIFFDataType.TIFF_NOTYPE: None,
    TIFFDataType.TIFF_BYTE: ctypes.c_ubyte,
    TIFFDataType.TIFF_ASCII: ctypes.c_char_p,
    TIFFDataType.TIFF_SHORT: ctypes.c_uint16,
    TIFFDataType.TIFF_LONG: ctypes.c_uint32,
    TIFFDataType.TIFF_RATIONAL: ctypes.c_double,  # Should be unsigned
    TIFFDataType.TIFF_SBYTE: ctypes.c_byte,
    TIFFDataType.TIFF_UNDEFINED: ctypes.c_char,
    TIFFDataType.TIFF_SSHORT: ctypes.c_int16,
    TIFFDataType.TIFF_SLONG: ctypes.c_int32,
    TIFFDataType.TIFF_SRATIONAL: ctypes.c_double,
    TIFFDataType.TIFF_FLOAT: ctypes.c_float,
    TIFFDataType.TIFF_DOUBLE: ctypes.c_double,
    TIFFDataType.TIFF_IFD: ctypes.c_uint32
}


class TIFFFieldInfo(ctypes.Structure):
    """
    typedef struct {
        ttag_t  field_tag;      /* field's tag */
        short   field_readcount;    /* read count/TIFF_VARIABLE/TIFF_SPP */
        short   field_writecount;   /* write count/TIFF_VARIABLE */
        TIFFDataType field_type;    /* type of associated data */
        unsigned short field_bit;   /* bit in fieldsset bit vector */
        unsigned char field_oktochange; /* if true, can change while writing */
        unsigned char field_passcount;  /* if true, pass dir count on set */
        char    *field_name;        /* ASCII name */
        } TIFFFieldInfo;
    """
    _fields_ = [
        ("field_tag", ctypes.c_uint32),
        ("field_readcount", ctypes.c_short),
        ("field_writecount", ctypes.c_short),
        ("field_type", TIFFDataType.ctype),
        ("field_bit", ctypes.c_ushort),
        ("field_oktochange", ctypes.c_ubyte),
        ("field_passcount", ctypes.c_ubyte),
        ("field_name", ctypes.c_char_p)
    ]


# Custom Tags
class TIFFExtender(object):
    def __init__(self, new_tag_list):
        self._ParentExtender = None
        self.new_tag_list = new_tag_list

        def extender_pyfunc(tiff_struct):
            libtiff.TIFFMergeFieldInfo(tiff_struct, self.new_tag_list,
                                       len(self.new_tag_list))

            if self._ParentExtender:
                self._ParentExtender(tiff_struct)

            # Just make being a void function more obvious
            return

        # ctypes callback function prototype (return void, arguments void
        # pointer)
        self.EXT_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
        # ctypes callback function instance
        self.EXT_FUNC_INST = self.EXT_FUNC(extender_pyfunc)

        libtiff.TIFFSetTagExtender.restype = ctypes.CFUNCTYPE(None,
                                                              ctypes.c_void_p)
        self._ParentExtender = libtiff.TIFFSetTagExtender(self.EXT_FUNC_INST)


def add_tags(tag_list):
    tag_list_array = (TIFFFieldInfo * len(tag_list))(*tag_list)
    for field_info in tag_list_array:
        _name = "TIFFTAG_" + str(field_info.field_name).upper()
        globals()[_name] = field_info.field_tag
        if field_info.field_writecount > 1 and field_info.field_type != \
                TIFFDataType.TIFF_ASCII:
            tifftags[field_info.field_tag] = (
                ttype2ctype[
                    field_info.field_type] * field_info.field_writecount,
                lambda _d: _d.contents[:])
        else:
            tifftags[field_info.field_tag] = (
                ttype2ctype[field_info.field_type], lambda _d: _d.value)

    return TIFFExtender(tag_list_array)


tifftags = {

    # TODO:
    # TIFFTAG_DOTRANGE                2      uint16*
    # TIFFTAG_HALFTONEHINTS           2      uint16*
    # TIFFTAG_PAGENUMBER              2      uint16*
    # TIFFTAG_YCBCRSUBSAMPLING        2      uint16*
    # TIFFTAG_EXTRASAMPLES            2      uint16*,uint16** count &
    #                                                         types array
    # TIFFTAG_FAXFILLFUNC             1      TIFFFaxFillFunc* G3/G4
    #                                                         compression
    #                                                         pseudo-tag
    # TIFFTAG_JPEGTABLES              2      u_short*,void**  count & tables
    # TIFFTAG_SUBIFD                  2      uint16*,uint32** count &
    #                                                         offsets array
    # TIFFTAG_TRANSFERFUNCTION        1 or 3 uint16**         1<<BitsPerSample
    #                                                         entry arrays
    # TIFFTAG_ICCPROFILE              2      uint32*,void**   count,
    #                                                         profile data

    # TIFFTAG: type, conversion  
    # 3 uint16* for Set, 3 uint16** for Get; size:(1<<BitsPerSample arrays)
    TIFFTAG_COLORMAP: (ctypes.c_uint16, lambda _d: (
        _d[0].contents[:], _d[1].contents[:], _d[2].contents[:])),
    TIFFTAG_ARTIST: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_COPYRIGHT: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_DATETIME: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_DOCUMENTNAME: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_HOSTCOMPUTER: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_IMAGEDESCRIPTION: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_INKNAMES: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_MAKE: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_MODEL: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_PAGENAME: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_SOFTWARE: (ctypes.c_char_p, lambda _d: _d.value),
    TIFFTAG_TARGETPRINTER: (ctypes.c_char_p, lambda _d: _d.value),

    TIFFTAG_BADFAXLINES: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_CONSECUTIVEBADFAXLINES: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_GROUP3OPTIONS: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_GROUP4OPTIONS: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_IMAGEDEPTH: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_IMAGEWIDTH: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_IMAGELENGTH: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_SAMPLESPERPIXEL: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_ROWSPERSTRIP: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_SUBFILETYPE: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_TILEDEPTH: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_TILELENGTH: (ctypes.c_uint32, lambda _d: _d.value),
    TIFFTAG_TILEWIDTH: (ctypes.c_uint32, lambda _d: _d.value),

    TIFFTAG_STRIPBYTECOUNTS: (
        ctypes.POINTER(ctypes.c_uint32), lambda _d: _d.contents),
    TIFFTAG_STRIPOFFSETS: (
        ctypes.POINTER(ctypes.c_uint32), lambda _d: _d.contents),
    TIFFTAG_TILEBYTECOUNTS: (
        ctypes.POINTER(ctypes.c_uint32), lambda _d: _d.contents),
    TIFFTAG_TILEOFFSETS: (
        ctypes.POINTER(ctypes.c_uint32), lambda _d: _d.contents),

    TIFFTAG_BITSPERSAMPLE: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_CLEANFAXDATA: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_COMPRESSION: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_DATATYPE: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_FILLORDER: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_INKSET: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_MATTEING: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_MAXSAMPLEVALUE: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_MINSAMPLEVALUE: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_ORIENTATION: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_PHOTOMETRIC: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_PLANARCONFIG: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_PREDICTOR: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_RESOLUTIONUNIT: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_SAMPLEFORMAT: (ctypes.c_uint16, lambda _d: _d.value),
    TIFFTAG_YCBCRPOSITIONING: (ctypes.c_uint16, lambda _d: _d.value),

    TIFFTAG_JPEGQUALITY: (ctypes.c_int, lambda _d: _d.value),
    TIFFTAG_JPEGCOLORMODE: (ctypes.c_int, lambda _d: _d.value),
    TIFFTAG_JPEGTABLESMODE: (ctypes.c_int, lambda _d: _d.value),
    TIFFTAG_FAXMODE: (ctypes.c_int, lambda _d: _d.value),

    TIFFTAG_SMAXSAMPLEVALUE: (ctypes.c_double, lambda _d: _d.value),
    TIFFTAG_SMINSAMPLEVALUE: (ctypes.c_double, lambda _d: _d.value),

    TIFFTAG_STONITS: (ctypes.c_double, lambda _d: _d.value),

    TIFFTAG_XPOSITION: (ctypes.c_float, lambda _d: _d.value),
    TIFFTAG_XRESOLUTION: (ctypes.c_float, lambda _d: _d.value),
    TIFFTAG_YPOSITION: (ctypes.c_float, lambda _d: _d.value),
    TIFFTAG_YRESOLUTION: (ctypes.c_float, lambda _d: _d.value),

    TIFFTAG_PRIMARYCHROMATICITIES: (
        ctypes.c_float * 6, lambda _d: _d.contents[:]),
    TIFFTAG_REFERENCEBLACKWHITE: (ctypes.c_float * 6, lambda _d:
                                  _d.contents[:]),
    TIFFTAG_WHITEPOINT: (ctypes.c_float * 2, lambda _d: _d.contents[:]),
    TIFFTAG_YCBCRCOEFFICIENTS: (ctypes.c_float * 3, lambda _d: _d.contents[:]),

    TIFFTAG_CZ_LSMINFO: (c_toff_t, lambda _d: _d.value)
    # offset to CZ_LSMINFO record

}


def debug(func):
    return func

    # def new_func(*args, **kws):
    #     print('Calling', func.__name__)
    #     r = func(*args, **kws)
    #     return r

    # return new_func


class TIFF(ctypes.c_void_p):
    """ Holds a pointer to TIFF object.

    To open a tiff file for reading, use

      tiff = TIFF.open (filename, more='r')
      
    To read an image from a tiff file, use

      image = tiff.read_image()

    where image will be a numpy array.

    To read all images from a tiff file, use

      for image in tiff.iter_images():
          # do stuff with image

    To creat a tiff file containing numpy array as image, use

      tiff = TIFF.open(filename, mode='w')
      tiff.write_image(array)
      tiff.close()

    To copy and change tags from a tiff file:

      tiff_in =  TIFF.open(filename_in)
      tiff_in.copy (filename_out, compression=, bitspersample=,
      sampleformat=,...)
    """

    @staticmethod
    def get_tag_name(tagvalue):
        for kind in define_to_name_map:
            tagname = define_to_name_map[kind].get(tagvalue)
            if tagname is not None:
                return tagname

    @staticmethod
    def get_tag_define(tagname):
        if '_' in tagname:
            kind, _name = tagname.rsplit('_', 1)
            return name_to_define_map[kind.title()][tagname.upper()]
        for kind in define_to_name_map:
            tagvalue = name_to_define_map[kind].get(
                (kind + '_' + tagname).upper())
            if tagvalue is not None:
                return tagvalue

    @classmethod
    def open(cls, filename, mode='r'):
        """ Open tiff file as TIFF.
        """
        tiff = libtiff.TIFFOpen(filename.encode('ascii'), mode.encode('ascii'))
        if tiff.value is None:
            raise TypeError('Failed to open file ' + repr(filename))
        return tiff

    @staticmethod
    def get_numpy_type(bits, sample_format=None):
        """ Return numpy dtype corresponding to bits and sample format.
        """
        if bits % 8 != 0:
            raise NotImplementedError("bits = {0:d}".format(bits))

        if sample_format == SAMPLEFORMAT_IEEEFP:
            typ = getattr(np, 'float%s' % bits)
        elif sample_format == SAMPLEFORMAT_UINT or sample_format is None:
            typ = getattr(np, 'uint%s' % bits)
        elif sample_format == SAMPLEFORMAT_INT:
            typ = getattr(np, 'int%s' % bits)
        elif sample_format == SAMPLEFORMAT_COMPLEXIEEEFP:
            typ = getattr(np, 'complex%s' % bits)
        else:
            raise NotImplementedError(repr(sample_format))
        return typ

    @debug
    def read_image(self, verbose=False):
        """ Read image from TIFF and return it as an array.
        """
        width = self.getfield('ImageWidth')
        height = self.getfield('ImageLength')
        samples_pp = self.getfield(
            'SamplesPerPixel')  # this number includes extra samples
        if samples_pp is None:  # default is 1
            samples_pp = 1
        # Note: In the TIFF specification, BitsPerSample and SampleFormat are
        # per samples. However, libtiff doesn't support mixed format,
        # so it will always return just one value (or raise an error).
        bits = self.getfield('BitsPerSample')
        sample_format = self.getfield('SampleFormat')
        planar_config = self.getfield('PlanarConfig')
        if planar_config is None:  # default is contig
            planar_config = PLANARCONFIG_CONTIG
        compression = self.getfield('Compression')
        if compression is None:  # default is no compression
            compression = COMPRESSION_NONE
        # TODO: rotate according to orientation

        # TODO: might need special support if bits < 8
        typ = self.get_numpy_type(bits, sample_format)

        if samples_pp == 1:
            # only 2 dimensions array
            arr = np.empty((height, width), typ)
        else:
            if planar_config == PLANARCONFIG_CONTIG:
                arr = np.empty((height, width, samples_pp), typ)
            elif planar_config == PLANARCONFIG_SEPARATE:
                arr = np.empty((samples_pp, height, width), typ)
            else:
                raise IOError("Unexpected PlanarConfig = %d" % planar_config)
        size = arr.nbytes

        if compression == COMPRESSION_NONE:
            readstrip = self.readrawstrip
        else:
            readstrip = self.readencodedstrip

        pos = 0
        for strip in range(self.numberofstrips()):
            elem = readstrip(strip, arr.ctypes.data + pos, max(size - pos, 0))
            pos += elem
        return arr

    @staticmethod
    def _fix_compression(_value):
        if isinstance(_value, int):
            return _value
        elif _value is None:
            return COMPRESSION_NONE
        elif isinstance(_value, str):
            return name_to_define_map['Compression'][
                'COMPRESSION_' + _value.upper()]
        else:
            raise NotImplementedError(repr(_value))

    @staticmethod
    def _fix_sampleformat(_value):
        if isinstance(_value, int):
            return _value
        elif _value is None:
            return SAMPLEFORMAT_UINT
        elif isinstance(_value, str):
            return dict(int=SAMPLEFORMAT_INT, uint=SAMPLEFORMAT_UINT,
                        float=SAMPLEFORMAT_IEEEFP,
                        complex=SAMPLEFORMAT_COMPLEXIEEEFP)[_value.lower()]
        else:
            raise NotImplementedError(repr(_value))

    def write_image(self, arr, compression=None, write_rgb=False):
        """ Write array as TIFF image.

        Parameters
        ----------
        arr : :numpy:`ndarray`
          Specify image data of rank 1 to 3.
        compression : {None, 'ccittrle', 'ccittfax3','ccitt_t4',
        'ccittfax4','ccitt_t6','lzw','ojpeg','jpeg','next','ccittrlew',
        'packbits','thunderscan','it8ctpad','it8lw','it8mp','it8bl',
        'pixarfilm','pixarlog','deflate','adobe_deflate','dcs','jbig',
        'sgilog','sgilog24','jp2000'}
        write_rgb: bool
          Write rgb image if data has 3 dimensions (otherwise, writes a
          multipage TIFF).
        """
        compression = self._fix_compression(compression)

        arr = np.ascontiguousarray(arr)
        if arr.dtype in np.sctypes['float']:
            sample_format = SAMPLEFORMAT_IEEEFP
        elif arr.dtype in np.sctypes['uint'] + [np.bool]:
            sample_format = SAMPLEFORMAT_UINT
        elif arr.dtype in np.sctypes['int']:
            sample_format = SAMPLEFORMAT_INT
        elif arr.dtype in np.sctypes['complex']:
            sample_format = SAMPLEFORMAT_COMPLEXIEEEFP
        else:
            raise NotImplementedError(repr(arr.dtype))
        shape = arr.shape
        bits = arr.itemsize * 8

        if compression == COMPRESSION_NONE:
            writestrip = self.writerawstrip
        else:
            writestrip = self.writeencodedstrip

        self.setfield(TIFFTAG_COMPRESSION, compression)
        if compression == COMPRESSION_LZW and sample_format in \
                [SAMPLEFORMAT_INT, SAMPLEFORMAT_UINT]:
            # This field can only be set after compression and before
            # writing data. Horizontal predictor often improves compression,
            # but some rare readers might support LZW only without predictor.
            self.setfield(TIFFTAG_PREDICTOR, PREDICTOR_HORIZONTAL)

        self.setfield(TIFFTAG_BITSPERSAMPLE, bits)
        self.setfield(TIFFTAG_SAMPLEFORMAT, sample_format)
        self.setfield(TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT)

        if len(shape) == 1:
            shape = (shape[0], 1)  # Same as 2D with height == 1

        if len(shape) == 2:
            height, width = shape
            size = width * height * arr.itemsize

            self.setfield(TIFFTAG_IMAGEWIDTH, width)
            self.setfield(TIFFTAG_IMAGELENGTH, height)
            self.setfield(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
            self.setfield(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
            writestrip(0, arr.ctypes.data, size)
            self.writedirectory()

        elif len(shape) == 3:
            if write_rgb:
                # Guess the planar config, with preference for separate planes
                if shape[2] == 3 or shape[2] == 4:
                    planar_config = PLANARCONFIG_CONTIG
                    height, width, depth = shape
                    size = arr.nbytes
                else:
                    planar_config = PLANARCONFIG_SEPARATE
                    depth, height, width = shape
                    size = width * height * arr.itemsize

                self.setfield(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB)
                self.setfield(TIFFTAG_IMAGEWIDTH, width)
                self.setfield(TIFFTAG_IMAGELENGTH, height)
                self.setfield(TIFFTAG_SAMPLESPERPIXEL, depth)
                self.setfield(TIFFTAG_PLANARCONFIG, planar_config)
                if depth == 4:  # RGBA
                    self.setfield(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNASSALPHA],
                                  count=1)
                elif depth > 4:  # No idea...
                    self.setfield(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNSPECIFIED] * (depth - 3),
                                  count=(depth - 3))

                if planar_config == PLANARCONFIG_CONTIG:
                    writestrip(0, arr.ctypes.data, size)
                else:
                    for _n in range(depth):
                        writestrip(_n, arr[_n, :, :].ctypes.data, size)
                self.writedirectory()
            else:
                depth, height, width = shape
                size = width * height * arr.itemsize
                for _n in range(depth):
                    self.setfield(TIFFTAG_IMAGEWIDTH, width)
                    self.setfield(TIFFTAG_IMAGELENGTH, height)
                    self.setfield(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
                    self.setfield(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)

                    writestrip(0, arr[_n].ctypes.data, size)
                    self.writedirectory()
        else:
            raise NotImplementedError(repr(shape))

    def write_tiles(self, arr):
        num_tcols = self.getfield("TileWidth")
        if num_tcols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to write tiles")
        num_trows = self.getfield("TileLength")
        if num_trows is None:
            num_trows = 1
        num_irows = self.getfield("ImageLength")
        if num_irows is None:
            num_irows = 1
        num_icols = self.getfield("ImageWidth")
        if num_icols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to write tiles")
        num_idepth = self.getfield("ImageDepth")
        if num_idepth is None:
            num_idepth = 1

        if len(arr.shape) == 1 and arr.shape[0] != num_icols:
            raise ValueError(
                "Input array %r must have the same shape as the image tags "
                "%r" % (arr.shape, (num_icols,)))
        if len(arr.shape) == 2 and (
                        arr.shape[0] != num_irows or
                        arr.shape[1] != num_icols):
            raise ValueError(
                "Input array %r must have same shape as image tags %r" % (
                    arr.shape, (num_irows, num_icols)))
        if len(arr.shape) == 3 and (
                            arr.shape[0] != num_idepth or
                            arr.shape[1] != num_irows or
                            arr.shape[2] != num_icols):
            raise ValueError(
                "Input array %r must have same shape as image tags %r" % (
                    arr.shape, (num_idepth, num_irows, num_icols)))
        if len(arr.shape) > 3:
            raise ValueError("Can not write tiles for more than 3 dimensions")

        status = 0
        tile_arr = np.zeros((num_trows, num_tcols), dtype=arr.dtype)
        # z direction / depth
        for z in range(0, num_idepth):
            # Rows
            for y in range(0, num_irows, num_trows):
                # Cols
                for x in range(0, num_icols, num_tcols):
                    # If we are over the edge of the image, use 0 as fill
                    tile_arr[:] = 0
                    if len(arr.shape) == 3:
                        if ((y + num_trows) > num_irows) or (
                                    (x + num_tcols) > num_icols):
                            tile_arr[:num_irows - y,
                                     :num_icols - x] = arr[z,
                                                           y:y + num_trows,
                                                           x:x + num_tcols]
                        else:
                            tile_arr[:, :] = arr[z,
                                                 y:y + num_trows,
                                                 x:x + num_tcols]
                    elif len(arr.shape) == 2:
                        if ((y + num_trows) > num_irows) or (
                                    (x + num_tcols) > num_icols):
                            tile_arr[:num_irows - y,
                                     :num_icols - x] = arr[y:y + num_trows,
                                                           x:x + num_tcols]
                        else:
                            tile_arr[:, :] = arr[y:y + num_trows,
                                                 x:x + num_tcols]
                    elif len(arr.shape) == 1:
                        # This doesn't make much sense for 1D arrays,
                        # waste of space if tiles are 2D
                        if (x + num_tcols) > num_icols:
                            tile_arr[0, :num_icols - x] = arr[x:x + num_tcols]
                        else:
                            tile_arr[0, :] = arr[x:x + num_tcols]

                    tile_arr = np.ascontiguousarray(tile_arr)
                    r = libtiff.TIFFWriteTile(self, tile_arr.ctypes.data, x, y,
                                              z, 0)
                    status = status + r.value

        return status

    def read_tiles(self, dtype=np.uint8):
        num_tcols = self.getfield("TileWidth")
        if num_tcols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to write tiles")
        num_trows = self.getfield("TileLength")
        if num_trows is None:
            num_trows = 1
        num_icols = self.getfield("ImageWidth")
        if num_icols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to write tiles")
        num_irows = self.getfield("ImageLength")
        if num_irows is None:
            num_irows = 1
        num_idepth = self.getfield("ImageDepth")
        if num_idepth is None:
            num_idepth = 1

        if num_idepth == 1 and num_irows == 1:
            # 1D
            full_image = np.zeros((num_icols,), dtype=dtype)
        elif num_idepth == 1:
            # 2D
            full_image = np.zeros((num_irows, num_icols), dtype=dtype)
        else:
            # 3D
            full_image = np.zeros((num_idepth, num_irows, num_icols),
                                  dtype=dtype)

        tmp_tile = np.zeros((num_trows, num_tcols), dtype=dtype)
        tmp_tile = np.ascontiguousarray(tmp_tile)
        for z in range(0, num_idepth):
            for y in range(0, num_irows, num_trows):
                for x in range(0, num_icols, num_tcols):
                    r = libtiff.TIFFReadTile(self, tmp_tile.ctypes.data, x, y,
                                             z, 0)
                    if not r:
                        raise ValueError(
                            "Could not read tile x:%d,y:%d,z:%d from file" % (
                                x, y, z))

                    if ((y + num_trows) > num_irows) or (
                                (x + num_tcols) > num_icols):
                        # We only need part of the tile because we are on
                        # the edge
                        if num_idepth == 1 and num_irows == 1:
                            full_image[x:x + num_tcols] = \
                                tmp_tile[0,:num_icols - x]
                        elif num_idepth == 1:
                            full_image[y:y + num_trows,
                                       x:x + num_tcols] = \
                                tmp_tile[:num_irows - y,
                                         :num_icols - x]
                        else:
                            full_image[z,
                                       y:y + num_trows,
                                       x:x + num_tcols] = \
                                tmp_tile[:num_irows - y,
                                         :num_icols - x]
                    else:
                        if num_idepth == 1 and num_irows == 1:
                            full_image[x:x + num_tcols] = tmp_tile[0, :]
                        elif num_idepth == 1:
                            full_image[y:y + num_trows,
                                       x:x + num_tcols] = tmp_tile[:, :]
                        else:
                            full_image[z, y:y + num_trows,
                                       x:x + num_tcols] = tmp_tile[:, :]

        return full_image

    def iter_images(self, verbose=False):
        """ Iterator of all images in a TIFF file.
        """
        yield self.read_image(verbose=verbose)
        while not self.lastdirectory():
            self.readdirectory()
            yield self.read_image(verbose=verbose)
        self.setdirectory(0)

    def __del__(self):
        self.close()

    @debug
    def filename(self):
        return libtiff.TIFFFileName(self)

    @debug
    def currentrow(self):
        return libtiff.TIFFCurrentRow(self)

    @debug
    def currentstrip(self):
        return libtiff.TIFFCurrentStrip(self)

    @debug
    def currenttile(self):
        return libtiff.TIFFCurrentTile(self)

    @debug
    def currentdirectory(self):
        return libtiff.TIFFCurrentDirectory(self)

    @debug
    def lastdirectory(self):
        return libtiff.TIFFLastDirectory(self)

    @debug
    def readdirectory(self):
        return libtiff.TIFFReadDirectory(self)

    @debug
    def writedirectory(self):
        r = libtiff.TIFFWriteDirectory(self)
        assert r == 1, repr(r)

    @debug
    def setdirectory(self, dirnum):
        return libtiff.TIFFSetDirectory(self, dirnum)

    @debug
    def fileno(self):
        return libtiff.TIFFFileno(self)

    @debug
    def getmode(self):
        return libtiff.TIFFGetMode(self)

    @debug
    def istiled(self):
        return libtiff.TIFFIsTiled(self)

    @debug
    def isbyteswapped(self):
        return libtiff.TIFFIsByteSwapped(self)

    @debug
    def isupsampled(self):
        return libtiff.TIFFIsUpSampled(self)

    # noinspection PyPep8Naming
    @debug
    def isMSB2LSB(self):
        return libtiff.TIFFIsMSB2LSB(self)

    @debug
    def numberofstrips(self):
        return libtiff.TIFFNumberOfStrips(self).value

    # @debug
    def readrawstrip(self, strip, buf, size):
        return libtiff.TIFFReadRawStrip(self, strip, buf, size).value

    def readencodedstrip(self, strip, buf, size):
        return libtiff.TIFFReadEncodedStrip(self, strip, buf, size).value

    def stripsize(self):
        return libtiff.TIFFStripSize(self).value

    def rawstripsize(self, strip):
        return libtiff.TIFFStripSize(self, strip).value

    @debug
    def writerawstrip(self, strip, buf, size):
        r = libtiff.TIFFWriteRawStrip(self, strip, buf, size)
        assert r.value == size, repr((r.value, size))

    @debug
    def writeencodedstrip(self, strip, buf, size):
        r = libtiff.TIFFWriteEncodedStrip(self, strip, buf, size)
        assert r.value == size, repr((r.value, size))

    closed = False

    def close(self, _libtiff=libtiff):
        if not self.closed and self.value is not None:
            _libtiff.TIFFClose(self)
            self.closed = True
        return

    # def (self): return libtiff.TIFF(self)

    @debug
    def getfield(self, tag, ignore_undefined_tag=True, count=None):
        """ Return TIFF field _value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """
        if tag in ['PixelSizeX', 'PixelSizeY', 'RelativeTime']:
            descr = self.getfield('ImageDescription')
            if not descr:
                return
            _i = descr.find(tag)
            if _i == -1:
                return
            _value = eval(descr[_i + len(tag):].lstrip().split()[0])
            return _value
        if isinstance(tag, str):
            tag = eval('TIFFTAG_' + tag.upper())
        t = tifftags.get(tag)
        if t is None:
            if not ignore_undefined_tag:
                print('Warning: no tag %r defined' % tag)
            return
        data_type, convert = t

        if tag == TIFFTAG_COLORMAP:
            bps = self.getfield("BitsPerSample")
            if bps is None:
                print(
                    "Warning: BitsPerSample is required to get ColorMap, "
                    "assuming 8 bps...")
                bps = 8
            num_cmap_elems = 1 << bps
            data_type *= num_cmap_elems
            pdt = ctypes.POINTER(data_type)
            rdata = pdt()
            gdata = pdt()
            bdata = pdt()
            rdata_ptr = ctypes.byref(rdata)
            gdata_ptr = ctypes.byref(gdata)
            bdata_ptr = ctypes.byref(bdata)

            # ignore count, it's not used for colormap
            libtiff.TIFFGetField.argtypes = libtiff.TIFFGetField.argtypes[
                                            :2] + [ctypes.c_void_p] * 3
            r = libtiff.TIFFGetField(self, tag, rdata_ptr, gdata_ptr,
                                     bdata_ptr)
            data = (rdata, gdata, bdata)
        else:
            if issubclass(data_type, ctypes.Array):
                pdt = ctypes.POINTER(data_type)
                data = pdt()
            else:
                data = data_type()

            if count is None:
                libtiff.TIFFGetField.argtypes = libtiff.TIFFGetField.argtypes[
                                                :2] + [ctypes.c_void_p]
                r = libtiff.TIFFGetField(self, tag, ctypes.byref(data))
            else:
                libtiff.TIFFGetField.argtypes = libtiff.TIFFGetField.argtypes[
                                                :2] + [ctypes.c_uint,
                                                       ctypes.c_void_p]
                r = libtiff.TIFFGetField(self, tag, count, ctypes.byref(data))
        if not r:  # tag not defined for current directory
            if not ignore_undefined_tag:
                print(
                    'Warning: tag %r not defined in currect directory' % tag)
            return None

        return convert(data)

    # @debug
    def setfield(self, tag, _value, count=None):
        """ Set TIFF field _value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """

        if isinstance(tag, str):
            tag = eval('TIFFTAG_' + tag.upper())
        t = tifftags.get(tag)
        if t is None:
            print('Warning: no tag %r defined' % tag)
            return
        data_type, convert = t
        if data_type == ctypes.c_float:
            data_type = ctypes.c_double

        if tag == TIFFTAG_COLORMAP:
            # ColorMap passes 3 values each a c_uint16 pointer
            try:
                r_arr, g_arr, b_arr = _value
            except (TypeError, ValueError):
                print(
                    "Error: TIFFTAG_COLORMAP expects 3 uint16* arrays as a "
                    "list/tuple of lists")
                r_arr, g_arr, b_arr = None, None, None
            if r_arr is None:
                return

            bps = self.getfield("BitsPerSample")
            if bps is None:
                print(
                    "Warning: BitsPerSample is required to get ColorMap, "
                    "assuming 8 bps...")
                bps = 8
            num_cmap_elems = 1 << bps
            data_type *= num_cmap_elems
            r_ptr = data_type(*r_arr)
            g_ptr = data_type(*g_arr)
            b_ptr = data_type(*b_arr)
            libtiff.TIFFSetField.argtypes = libtiff.TIFFSetField.argtypes[
                                            :2] + [ctypes.POINTER(
                                                   data_type)] * 3
            r = libtiff.TIFFSetField(self, tag, r_ptr, g_ptr, b_ptr)
        else:
            if issubclass(data_type, (ctypes.Array, tuple, list)):
                data = data_type(*_value)
            elif issubclass(data_type,
                            ctypes._Pointer):  # does not include c_char_p
                # convert to the base type, ctypes will take care of actually
                # sending it by reference
                base_type = data_type._type_
                if isinstance(_value, collections.Iterable):
                    data = base_type(*_value)
                else:
                    data = base_type(_value)
            else:
                data = data_type(_value)

            # TODO: for most of the tags, count is len(_value),
            # so it shouldn't be needed
            if count is None:
                libtiff.TIFFSetField.argtypes = libtiff.TIFFSetField.argtypes[
                                                :2] + [data_type]
                r = libtiff.TIFFSetField(self, tag, data)
            else:
                libtiff.TIFFSetField.argtypes = libtiff.TIFFSetField.argtypes[
                                                :2] + [ctypes.c_uint,
                                                       data_type]
                r = libtiff.TIFFSetField(self, tag, count, data)
        return r

    def info(self):
        """ Return a string containing <tag name: field value> map.
        """
        _l = ['filename: %s' % (self.filename())]
        for tagname in ['Artist', 'CopyRight', 'DateTime', 'DocumentName',
                        'HostComputer', 'ImageDescription', 'InkNames',
                        'Make', 'Model', 'PageName', 'Software',
                        'TargetPrinter',
                        'BadFaxLines', 'ConsecutiveBadFaxLines',
                        'Group3Options', 'Group4Options',
                        'ImageDepth', 'ImageWidth', 'ImageLength',
                        'RowsPerStrip', 'SubFileType',
                        'TileDepth', 'TileLength', 'TileWidth',
                        'StripByteCounts', 'StripOffSets',
                        'TileByteCounts', 'TileOffSets',
                        'BitsPerSample', 'CleanFaxData', 'Compression',
                        'DataType', 'FillOrder', 'InkSet', 'Matteing',
                        'MaxSampleValue', 'MinSampleValue', 'Orientation',
                        'PhotoMetric', 'PlanarConfig', 'Predictor',
                        'ResolutionUnit', 'SampleFormat', 'YCBCRPositioning',
                        'JPEGQuality', 'JPEGColorMode', 'JPEGTablesMode',
                        'FaxMode', 'SMaxSampleValue', 'SMinSampleValue',
                        # 'Stonits',
                        'XPosition', 'YPosition', 'XResolution', 'YResolution',
                        'PrimaryChromaticities', 'ReferenceBlackWhite',
                        'WhitePoint', 'YCBCRCoefficients',
                        'PixelSizeX', 'PixelSizeY', 'RelativeTime',
                        'CZ_LSMInfo'
                        ]:
            v = self.getfield(tagname)
            if v:
                if isinstance(v, int):
                    v = define_to_name_map.get(tagname, {}).get(v, v)
                _l.append('%s: %s' % (tagname, v))
                if tagname == 'CZ_LSMInfo':
                    print(CZ_LSMInfo(self))
        return '\n'.join(_l)

    def copy(self, filename, **kws):
        """ Copy opened TIFF file to a new file.

        Use keyword arguments to redefine tag values.

        Parameters
        ----------
        filename : str
          Specify the name of file where TIFF file is copied to.
        compression : {'none', 'lzw', 'deflate', ...}
          Specify compression scheme.
        bitspersample : {8,16,32,64,128,256}
          Specify bit size of a sample.
        sampleformat : {'uint', 'int', 'float', 'complex'}
          Specify sample format.
        """
        other = TIFF.open(filename, mode='w')
        define_rewrite = {}
        for _name, _value in list(kws.items()):
            define = TIFF.get_tag_define(_name)
            assert define is not None
            if _name == 'compression':
                _value = TIFF._fix_compression(_value)
            if _name == 'sampleformat':
                _value = TIFF._fix_sampleformat(_value)
            define_rewrite[define] = _value
        name_define_list = list(name_to_define_map['TiffTag'].items())
        self.setdirectory(0)
        self.readdirectory()
        while 1:
            other.setdirectory(self.currentdirectory())
            bits = self.getfield('BitsPerSample')
            sample_format = self.getfield('SampleFormat')
            assert bits >= 8, repr((bits, sample_format, dtype))
            itemsize = bits // 8
            dtype = self.get_numpy_type(bits, sample_format)
            for _name, define in name_define_list:
                orig_value = self.getfield(define)
                if orig_value is None and define not in define_rewrite:
                    continue
                if _name.endswith('OFFSETS') or _name.endswith('BYTECOUNTS'):
                    continue
                if define in define_rewrite:
                    _value = define_rewrite[define]
                else:
                    _value = orig_value
                if _value is None:
                    continue
                other.setfield(define, _value)
            new_bits = other.getfield('BitsPerSample')
            new_sample_format = other.getfield('SampleFormat')
            new_dtype = other.get_numpy_type(new_bits, new_sample_format)
            assert new_bits >= 8, repr(
                (new_bits, new_sample_format, new_dtype))
            new_itemsize = new_bits // 8
            strip_size = self.stripsize()
            buf = np.zeros(strip_size // itemsize, dtype)
            for strip in range(self.numberofstrips()):
                elem = self.readencodedstrip(strip, buf.ctypes.data,
                                             strip_size)
                if elem > 0:
                    new_buf = buf.astype(new_dtype)
                    other.writeencodedstrip(strip, new_buf.ctypes.data,
                                            (elem * new_itemsize) // itemsize)
            self.readdirectory()
            if self.lastdirectory():
                break
        other.close()


class TIFF3D(TIFF):
    """ subclass of TIFF for handling import of 3D (multi-directory) files.
    
    like TIFF, but TIFF3D.read_image() will attempt to restore a 3D numpy array
    when given a multi-image TIFF file; performing the inverse of
    
    TIFF_instance.write(numpy.zeros((40, 200, 200)))
    
    like so:
    
    arr = TIFF3D_instance.read_image()
    arr.shape # gives (40, 200, 200)
    
    if you tried this with a normal TIFF instance, you would get this:
    
    arr = TIFF_instance.read_image()
    arr.shape # gives (200, 200)
    
    and you would have to loop over each image by hand with TIFF.iter_images().
    """

    @classmethod
    def open(cls, filename, mode='r'):
        """ just like TIFF.open, except returns a TIFF3D instance.
        """
        # monkey-patch the restype:
        old_restype = libtiff.TIFFOpen.restype
        libtiff.TIFFOpen.restype = TIFF3D

        # actually call the library function:
        tiff = libtiff.TIFFOpen(filename, mode)

        # restore the old restype:
        libtiff.TIFFOpen.restype = old_restype
        if tiff.value is None:
            raise TypeError('Failed to open file ' + repr(filename))
        return tiff

    @debug
    def read_image(self, verbose=False, as3d=True):
        """ Read image from TIFF and return it as a numpy array.
        
        If as3d is passed True (default), will attempt to read multiple
        directories, and restore as slices in a 3D array. ASSUMES that all
        images in the tiff file have the same width, height, bits-per-sample,
        compression, and so on. If you get a segfault, this is probably the
        problem.
        """
        if not as3d:
            return TIFF.read_image(self, verbose)

        # Code is initially copy-paste from TIFF:
        width = self.getfield('ImageWidth')
        height = self.getfield('ImageLength')
        bits = self.getfield('BitsPerSample')
        sample_format = self.getfield('SampleFormat')
        compression = self.getfield('Compression')

        typ = self.get_numpy_type(bits, sample_format)

        if typ is None:
            if bits == 1:
                typ = np.uint8
                itemsize = 1
            elif bits == 4:
                typ = np.uint32
                itemsize = 4
            else:
                raise NotImplementedError(repr(bits))
        else:
            itemsize = bits / 8

        # in order to allocate the numpy array, we must count the directories:
        # code borrowed from TIFF.iter_images():
        depth = 0
        while True:
            depth += 1
            if self.lastdirectory():
                break
            self.readdirectory()
        self.setdirectory(0)

        # we proceed assuming all directories have the same properties from
        # above.
        layer_size = width * height * itemsize
        # total_size = layer_size * depth
        arr = np.zeros((depth, height, width), typ)

        if compression == COMPRESSION_NONE:
            readstrip = self.readrawstrip
        else:
            readstrip = self.readencodedstrip

        layer = 0
        while True:
            pos = 0
            elem = None
            for strip in range(self.numberofstrips()):
                if elem is None:
                    elem = readstrip(strip,
                                     arr.ctypes.data + layer * layer_size +
                                     pos,
                                     layer_size)
                elif elem:
                    elem = readstrip(strip,
                                     arr.ctypes.data + layer * layer_size +
                                     pos,
                                     min(layer_size - pos, elem))
                pos += elem
            if self.lastdirectory():
                break
            self.readdirectory()
            layer += 1
        self.setdirectory(0)
        return arr


class CZ_LSMInfo:
    def __init__(self, tiff):
        self.tiff = tiff
        self.filename = tiff.filename()
        self.offset = tiff.getfield(TIFFTAG_CZ_LSMINFO)
        self.extract_info()

    def extract_info(self):
        if self.offset is None:
            return
        _f = libtiff.TIFFFileno(self.tiff)
        fd = os.fdopen(_f, 'r')
        pos = fd.tell()
        self.offset = self.tiff.getfield(TIFFTAG_CZ_LSMINFO)
        print(os.lseek(_f, 0, 1))

        print(pos)
        # print libtiff.TIFFSeekProc(self.tiff, 0, 1)
        fd.seek(0)
        print(struct.unpack('HH', fd.read(4)))
        print(struct.unpack('I', fd.read(4)))
        print(struct.unpack('H', fd.read(2)))
        fd.seek(self.offset)
        _d = [('magic_number', 'i4'),
              ('structure_size', 'i4')]
        print(pos, np.rec.fromfile(fd, _d, 1))
        fd.seek(pos)
        # print hex (struct.unpack('I', fd.read (4))[0])
        # fd.close()

    def __str__(self):
        return '%s: %s' % (self.filename, self.offset)


libtiff.TIFFOpen.restype = TIFF
libtiff.TIFFOpen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

libtiff.TIFFFileName.restype = ctypes.c_char_p
libtiff.TIFFFileName.argtypes = [TIFF]

libtiff.TIFFFileno.restype = ctypes.c_int
libtiff.TIFFFileno.argtypes = [TIFF]

libtiff.TIFFCurrentRow.restype = ctypes.c_uint32
libtiff.TIFFCurrentRow.argtypes = [TIFF]

libtiff.TIFFCurrentStrip.restype = c_tstrip_t
libtiff.TIFFCurrentStrip.argtypes = [TIFF]

libtiff.TIFFCurrentTile.restype = c_ttile_t
libtiff.TIFFCurrentTile.argtypes = [TIFF]

libtiff.TIFFCurrentDirectory.restype = c_tdir_t
libtiff.TIFFCurrentDirectory.argtypes = [TIFF]

libtiff.TIFFLastDirectory.restype = ctypes.c_int
libtiff.TIFFLastDirectory.argtypes = [TIFF]

libtiff.TIFFReadDirectory.restype = ctypes.c_int
libtiff.TIFFReadDirectory.argtypes = [TIFF]

libtiff.TIFFWriteDirectory.restype = ctypes.c_int
libtiff.TIFFWriteDirectory.argtypes = [TIFF]

libtiff.TIFFSetDirectory.restype = ctypes.c_int
libtiff.TIFFSetDirectory.argtypes = [TIFF, c_tdir_t]

libtiff.TIFFFileno.restype = ctypes.c_int
libtiff.TIFFFileno.argtypes = [TIFF]

libtiff.TIFFGetMode.restype = ctypes.c_int
libtiff.TIFFGetMode.argtypes = [TIFF]

libtiff.TIFFIsTiled.restype = ctypes.c_int
libtiff.TIFFIsTiled.argtypes = [TIFF]

libtiff.TIFFIsByteSwapped.restype = ctypes.c_int
libtiff.TIFFIsByteSwapped.argtypes = [TIFF]

libtiff.TIFFIsUpSampled.restype = ctypes.c_int
libtiff.TIFFIsUpSampled.argtypes = [TIFF]

libtiff.TIFFIsMSB2LSB.restype = ctypes.c_int
libtiff.TIFFIsMSB2LSB.argtypes = [TIFF]

libtiff.TIFFGetField.restype = ctypes.c_int
libtiff.TIFFGetField.argtypes = [TIFF, c_ttag_t, ctypes.c_void_p]

libtiff.TIFFSetField.restype = ctypes.c_int
libtiff.TIFFSetField.argtypes = [TIFF, c_ttag_t,
                                 ctypes.c_void_p]  # last item is reset in
#                                                    TIFF.setfield method

libtiff.TIFFNumberOfStrips.restype = c_tstrip_t
libtiff.TIFFNumberOfStrips.argtypes = [TIFF]

libtiff.TIFFReadRawStrip.restype = c_tsize_t
libtiff.TIFFReadRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFWriteRawStrip.restype = c_tsize_t
libtiff.TIFFWriteRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFReadEncodedStrip.restype = c_tsize_t
libtiff.TIFFReadEncodedStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t,
                                         c_tsize_t]

libtiff.TIFFWriteEncodedStrip.restype = c_tsize_t
libtiff.TIFFWriteEncodedStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t,
                                          c_tsize_t]

libtiff.TIFFStripSize.restype = c_tsize_t
libtiff.TIFFStripSize.argtypes = [TIFF]

libtiff.TIFFRawStripSize.restype = c_tsize_t
libtiff.TIFFRawStripSize.argtypes = [TIFF, c_tstrip_t]

# For adding custom tags (must be void pointer otherwise callback seg faults
libtiff.TIFFMergeFieldInfo.restype = ctypes.c_int32
libtiff.TIFFMergeFieldInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_uint32]

# Tile Support
# TODO:
#   TIFFTileRowSize64
#   TIFFTileSize64
#   TIFFVTileSize
#   TIFFVTileSize64
libtiff.TIFFTileRowSize.restype = c_tsize_t
libtiff.TIFFTileRowSize.argtypes = [TIFF]

libtiff.TIFFTileSize.restype = c_tsize_t
libtiff.TIFFTileSize.argtypes = [TIFF]

libtiff.TIFFComputeTile.restype = c_ttile_t
libtiff.TIFFComputeTile.argtypes = [TIFF, ctypes.c_uint32, ctypes.c_uint32,
                                    ctypes.c_uint32, c_tsample_t]

libtiff.TIFFCheckTile.restype = ctypes.c_int
libtiff.TIFFCheckTile.argtypes = [TIFF, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_uint32, c_tsample_t]

libtiff.TIFFNumberOfTiles.restype = c_ttile_t
libtiff.TIFFNumberOfTiles.argtypes = [TIFF]

libtiff.TIFFReadTile.restype = c_tsize_t
libtiff.TIFFReadTile.argtypes = [TIFF, c_tdata_t, ctypes.c_uint32,
                                 ctypes.c_uint32, ctypes.c_uint32, c_tsample_t]

libtiff.TIFFWriteTile.restype = c_tsize_t
libtiff.TIFFWriteTile.argtypes = [TIFF, c_tdata_t, ctypes.c_uint32,
                                  ctypes.c_uint32, ctypes.c_uint32,
                                  c_tsample_t]

libtiff.TIFFReadEncodedTile.restype = ctypes.c_int
libtiff.TIFFReadEncodedTile.argtypes = [TIFF, ctypes.c_ulong, ctypes.c_char_p,
                                        ctypes.c_ulong]

libtiff.TIFFReadRawTile.restype = c_tsize_t
libtiff.TIFFReadRawTile.argtypes = [TIFF, c_ttile_t, c_tdata_t, c_tsize_t]

libtiff.TIFFReadRGBATile.restype = ctypes.c_int
libtiff.TIFFReadRGBATile.argtypes = [TIFF, ctypes.c_uint32, ctypes.c_uint32,
                                     ctypes.POINTER(ctypes.c_uint32)]

libtiff.TIFFWriteEncodedTile.restype = c_tsize_t
libtiff.TIFFWriteEncodedTile.argtypes = [TIFF, c_ttile_t, c_tdata_t, c_tsize_t]

libtiff.TIFFWriteRawTile.restype = c_tsize_t
libtiff.TIFFWriteRawTile.argtypes = [TIFF, c_ttile_t, c_tdata_t, c_tsize_t]

libtiff.TIFFDefaultTileSize.restype = None
libtiff.TIFFDefaultTileSize.argtypes = [TIFF, ctypes.c_uint32, ctypes.c_uint32]

libtiff.TIFFClose.restype = None
libtiff.TIFFClose.argtypes = [TIFF]

# Support for TIFF warning and error handlers:
TIFFWarningHandler = ctypes.CFUNCTYPE(None,
                                      ctypes.c_char_p,  # Module
                                      ctypes.c_char_p,  # Format
                                      ctypes.c_void_p)  # va_list
TIFFErrorHandler = ctypes.CFUNCTYPE(None,
                                    ctypes.c_char_p,  # Module
                                    ctypes.c_char_p,  # Format
                                    ctypes.c_void_p)  # va_list

# This has to be at module scope so it is not garbage-collected
_null_warning_handler = TIFFWarningHandler(lambda module, fmt, va_list: None)
_null_error_handler = TIFFErrorHandler(lambda module, fmt, va_list: None)


def suppress_warnings():
    libtiff.TIFFSetWarningHandler(_null_warning_handler)


def suppress_errors():
    libtiff.TIFFSetErrorHandler(_null_error_handler)


def _test_custom_tags():
    def _tag_write():
        a = TIFF.open("/tmp/libtiff_test_custom_tags.tif", "w")

        a.setfield("ARTIST", "MY NAME")
        a.setfield("LibtiffTestByte", 42)
        a.setfield("LibtiffTeststr", "FAKE")
        a.setfield("LibtiffTestuint16", 42)
        a.setfield("LibtiffTestMultiuint32", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
        a.setfield("XPOSITION", 42.0)
        a.setfield("PRIMARYCHROMATICITIES", (1.0, 2, 3, 4, 5, 6))

        arr = np.ones((512, 512), dtype=np.uint8)
        arr[:, :] = 255
        a.write_image(arr)

        print("Tag Write: SUCCESS")

    def _tag_read():
        a = TIFF.open("/tmp/libtiff_test_custom_tags.tif", "r")

        tmp = a.read_image()
        assert tmp.shape == (
            512,
            512), "Image read was wrong shape (%r instead of (512,512))" % (
            tmp.shape,)
        tmp = a.getfield("XPOSITION")
        assert tmp == 42.0, "XPosition was not read as 42.0"
        tmp = a.getfield("ARTIST")
        assert tmp == "MY NAME", "Artist was not read as 'MY NAME'"
        tmp = a.getfield("LibtiffTestByte")
        assert tmp == 42, "LibtiffTestbyte was not read as 42"
        tmp = a.getfield("LibtiffTestuint16")
        assert tmp == 42, "LibtiffTestuint16 was not read as 42"
        tmp = a.getfield("LibtiffTestMultiuint32")
        assert tmp == [1, 2, 3, 4, 5, 6, 7, 8, 9,
                       10], "LibtiffTestMultiuint32 was not read as [1,2,3," \
                            "4,5,6,7,8,9,10]"
        tmp = a.getfield("LibtiffTeststr")
        assert tmp == "FAKE", "LibtiffTeststr was not read as 'FAKE'"
        tmp = a.getfield("PRIMARYCHROMATICITIES")
        assert tmp == [1.0, 2.0, 3.0, 4.0, 5.0,
                       6.0], "PrimaryChromaticities was not read as [1.0," \
                             "2.0,3.0,4.0,5.0,6.0]"
        print("Tag Read: SUCCESS")

    # Define a C structure that says how each tag should be used
    test_tags = [
        TIFFFieldInfo(40100, 1, 1, TIFFDataType.TIFF_BYTE, FIELD_CUSTOM, True,
                      False, "LibtiffTestByte"),
        TIFFFieldInfo(40103, 10, 10, TIFFDataType.TIFF_LONG, FIELD_CUSTOM,
                      True, False, "LibtiffTestMultiuint32"),
        TIFFFieldInfo(40102, 1, 1, TIFFDataType.TIFF_SHORT, FIELD_CUSTOM, True,
                      False, "LibtiffTestuint16"),
        TIFFFieldInfo(40101, -1, -1, TIFFDataType.TIFF_ASCII, FIELD_CUSTOM,
                      True, False, "LibtiffTeststr")
    ]

    # Add tags to the libtiff library
    test_extender = add_tags(
        test_tags)  # Keep pointer to extender object, no gc
    _tag_write()
    _tag_read()


def _test_tile_write():
    a = TIFF.open("/tmp/libtiff_test_tile_write.tiff", "w")

    # 1D Arrays (doesn't make much sense to tile)
    assert a.setfield("ImageWidth",
                      3000) == 1, "could not set ImageWidth tag"  # 1D,2D,3D
    assert a.setfield("ImageLength",
                      1) == 1, "could not set ImageLength tag"  # 1D
    assert a.setfield("ImageDepth",
                      1) == 1, "could not set ImageDepth tag"  # 1D,2D
    # Must be multiples of 16
    assert a.setfield("TileWidth", 512) == 1, "could not set TileWidth tag"
    assert a.setfield("TileLength", 528) == 1, "could not set TileLength tag"
    assert a.setfield("BitsPerSample",
                      8) == 1, "could not set BitsPerSample tag"
    assert a.setfield("Compression",
                      COMPRESSION_NONE) == 1, "could not set Compression tag"
    data_array = np.array(list(range(500)) * 6).astype(np.uint8)
    assert a.write_tiles(data_array) == (
                                            512 * 528) * 6, "could " \
                                                            "not write " \
                                                            "tile images"  # 1D
    a.writedirectory()
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 2D Arrays
    assert a.setfield("ImageWidth",
                      3000) == 1, "could not set ImageWidth tag"  # 1D,2D,3D
    assert a.setfield("ImageLength",
                      2500) == 1, "could not set ImageLength tag"  # 2D,3D
    assert a.setfield("ImageDepth",
                      1) == 1, "could not set ImageDepth tag"  # 1D,2D
    # Must be multiples of 16
    assert a.setfield("TileWidth", 512) == 1, "could not set TileWidth tag"
    assert a.setfield("TileLength", 528) == 1, "could not set TileLength tag"
    assert a.setfield("BitsPerSample",
                      8) == 1, "could not set BitsPerSample tag"
    assert a.setfield("Compression",
                      COMPRESSION_NONE) == 1, "could not set Compression tag"
    data_array = np.tile(list(range(500)), (2500, 6)).astype(np.uint8)
    assert a.write_tiles(data_array) == (
                                            512 * 528) * 5 * 6, "could not " \
                                                                "write tile " \
                                                                "images"  # 2D
    a.writedirectory()
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 3D Arrays
    assert a.setfield("ImageWidth",
                      3000) == 1, "could not set ImageWidth tag"  # 1D,2D,3D
    assert a.setfield("ImageLength",
                      2500) == 1, "could not set ImageLength tag"  # 2D,3D
    assert a.setfield("ImageDepth",
                      3) == 1, "could not set ImageDepth tag"  # 3D
    assert a.setfield("TileWidth", 512) == 1, "could not set TileWidth tag"
    assert a.setfield("TileLength", 528) == 1, "could not set TileLength tag"
    assert a.setfield("BitsPerSample",
                      8) == 1, "could not set BitsPerSample tag"
    assert a.setfield("Compression",
                      COMPRESSION_NONE) == 1, "could not set Compression tag"
    data_array = np.tile(list(range(500)), (3, 2500, 6)).astype(np.uint8)
    assert a.write_tiles(data_array) == (512 * 528) * 5 * 6 * 3, "could " \
                                                                 "not " \
                                                                 "write " \
                                                                 "tile " \
                                                                 "images"  # 3D
    a.writedirectory()
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    print("Tile Write: SUCCESS")


def _test_tile_read(filename=None):
    import sys
    if filename is None:
        if len(sys.argv) != 2:
            print("Run `libtiff.py <filename>` for testing.")
            return
        filename = sys.argv[1]

    a = TIFF.open(filename, "r")

    # 1D Arrays (doesn't make much sense to tile)
    a.setdirectory(0)
    iwidth = tmp = a.getfield("ImageWidth")
    assert tmp is not None, "ImageWidth tag must be defined for reading tiles"
    ilength = tmp = a.getfield("ImageLength")
    assert tmp is not None, "ImageLength tag must be defined for reading tiles"
    idepth = tmp = a.getfield("ImageDepth")
    assert tmp is not None, "ImageDepth tag must be defined for reading tiles"
    tmp = a.getfield("TileWidth")
    assert tmp is not None, "TileWidth tag must be defined for reading tiles"
    tmp = a.getfield("TileLength")
    assert tmp is not None, "TileLength tag must be defined for reading tiles"
    tmp = a.getfield("BitsPerSample")
    assert tmp is not None, "BitsPerSample tag must be defined for reading " \
                            "tiles"
    tmp = a.getfield("Compression")
    assert tmp is not None, "Compression tag must be defined for reading tiles"

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (iwidth,), "tile data read was the wrong shape"
    test_array = np.array(list(range(500)) * 6).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[
               0] == 0, "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # 2D Arrays (doesn't make much sense to tile)
    a.setdirectory(1)
    iwidth = tmp = a.getfield("ImageWidth")
    assert tmp is not None, "ImageWidth tag must be defined for reading tiles"
    ilength = tmp = a.getfield("ImageLength")
    assert tmp is not None, "ImageLength tag must be defined for reading tiles"
    idepth = tmp = a.getfield("ImageDepth")
    assert tmp is not None, "ImageDepth tag must be defined for reading tiles"
    tmp = a.getfield("TileWidth")
    assert tmp is not None, "TileWidth tag must be defined for reading tiles"
    tmp = a.getfield("TileLength")
    assert tmp is not None, "TileLength tag must be defined for reading tiles"
    tmp = a.getfield("BitsPerSample")
    assert tmp is not None, "BitsPerSample tag must be defined for reading " \
                            "tiles"
    tmp = a.getfield("Compression")
    assert tmp is not None, "Compression tag must be defined for reading tiles"

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (
        ilength, iwidth), "tile data read was the wrong shape"
    test_array = np.tile(list(range(500)), (2500, 6)).astype(
        np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[
               0] == 0, "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    # 3D Arrays (doesn't make much sense to tile)
    a.setdirectory(2)
    iwidth = tmp = a.getfield("ImageWidth")
    assert tmp is not None, "ImageWidth tag must be defined for reading tiles"
    ilength = tmp = a.getfield("ImageLength")
    assert tmp is not None, "ImageLength tag must be defined for reading tiles"
    idepth = tmp = a.getfield("ImageDepth")
    assert tmp is not None, "ImageDepth tag must be defined for reading tiles"
    tmp = a.getfield("TileWidth")
    assert tmp is not None, "TileWidth tag must be defined for reading tiles"
    tmp = a.getfield("TileLength")
    assert tmp is not None, "TileLength tag must be defined for reading tiles"
    tmp = a.getfield("BitsPerSample")
    assert tmp is not None, "BitsPerSample tag must be defined for reading " \
                            "tiles"
    tmp = a.getfield("Compression")
    assert tmp is not None, "Compression tag must be defined for reading tiles"

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (
        idepth, ilength, iwidth), "tile data read was the wrong shape"
    test_array = np.tile(list(range(500)), (3, 2500, 6)).astype(
        np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[
               0] == 0, "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")
    print("Tile Read: SUCCESS")


def _test_tags_write():
    tiff = TIFF.open('/tmp/libtiff_tags_write.tiff', mode='w')
    tmp = tiff.setfield("Artist", "A Name")
    assert tmp == 1, "Tag 'Artist' was not written properly"
    tmp = tiff.setfield("DocumentName", "")
    assert tmp == 1, "Tag 'DocumentName' with empty string was not written " \
                     "properly"
    tmp = tiff.setfield("PrimaryChromaticities", [1, 2, 3, 4, 5, 6])
    assert tmp == 1, "Tag 'PrimaryChromaticities' was not written properly"
    tmp = tiff.setfield("BitsPerSample", 8)
    assert tmp == 1, "Tag 'BitsPerSample' was not written properly"
    tmp = tiff.setfield("ColorMap", [[x * 256 for x in range(256)]] * 3)
    assert tmp == 1, "Tag 'ColorMap' was not written properly"

    arr = np.zeros((100, 100), np.uint8)
    tiff.write_image(arr)

    print("Tag Write: SUCCESS")


def _test_tags_read(filename=None):
    import sys
    if filename is None:
        if len(sys.argv) != 2:
            filename = '/tmp/libtiff_tags_write.tiff'
            if not os.path.isfile(filename):
                print('Run `%s <filename>` for testing.' % (__file__))
                return
        else:
            filename = sys.argv[1]
    tiff = TIFF.open(filename)
    tmp = tiff.getfield("Artist")
    assert tmp == "A Name", "Tag 'Artist' did not read the correct value (" \
                            "Got '%s'; Expected 'A Name')" % (
        tmp,)
    tmp = tiff.getfield("DocumentName")
    assert tmp == "", "Tag 'DocumentName' did not read the correct value (" \
                      "Got '%s'; Expected empty string)" % (
        tmp,)
    tmp = tiff.getfield("PrimaryChromaticities")
    assert tmp == [1, 2, 3, 4, 5,
                   6], "Tag 'PrimaryChromaticities' did not read the " \
                       "correct value (Got '%r'; Expected '[1,2,3,4,5,6]'" % (
        tmp,)
    tmp = tiff.getfield("BitsPerSample")
    assert tmp == 8, "Tag 'BitsPerSample' did not read the correct value (" \
                     "Got %s; Expected 8)" % (str(tmp),)
    tmp = tiff.getfield("ColorMap")
    try:
        assert len(
            tmp) == 3, "Tag 'ColorMap' should be three arrays, found %d" % \
                       len(tmp)
        assert len(tmp[
                       0]) == 256, "Tag 'ColorMap' should be three arrays " \
                                   "of 256 elements, found %d elements" % \
                                   len(tmp[0])
        assert len(tmp[
                       1]) == 256, "Tag 'ColorMap' should be three arrays " \
                                   "of 256 elements, found %d elements" % \
                                   len(tmp[1])
        assert len(tmp[
                       2]) == 256, "Tag 'ColorMap' should be three arrays " \
                                   "of 256 elements, found %d elements" % \
                                   len(tmp[2])
    except TypeError:
        print(
            "Tag 'ColorMap' has the wrong shape of 3 arrays of 256 elements "
            "each")
        return

    print("Tag Read: SUCCESS")


def _test_read(filename=None):
    import sys
    import time
    if filename is None:
        if len(sys.argv) != 2:
            filename = '/tmp/libtiff_test_write.tiff'
            if not os.path.isfile(filename):
                print('Run `libtiff.py <filename>` for testing.')
                return
        else:
            filename = sys.argv[1]
    print('Trying to open', filename, '...', end=' ')
    tiff = TIFF.open(filename)
    print('ok')
    print('Trying to show info ...\n', '-' * 10)
    print(tiff.info())
    print('-' * 10, 'ok')
    print('Trying show images ...')
    t = time.time()
    _i = 0
    for image in tiff.iter_images(verbose=True):
        # print image.min(), image.max(), image.mean ()
        _i += 1
    print('\tok', (time.time() - t) * 1e3, 'ms', _i, 'images')


def _test_write():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = _i + 10 * j
    print(arr)
    tiff.write_image(arr)
    del tiff


def _test_write_float():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6), np.float64)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = _i + 10 * j
    print(arr)
    tiff.write_image(arr)
    del tiff

    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()
    print(arr2)


def _test_copy():
    tiff = TIFF.open('/tmp/libtiff_test_compression.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = 1 + _i + 10 * j
    # from scipy.stats import poisson
    # arr = poisson.rvs (arr)
    tiff.setfield('ImageDescription', 'Hey\nyou')
    tiff.write_image(arr, compression='lzw')
    del tiff

    tiff = TIFF.open('/tmp/libtiff_test_compression.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()

    assert (arr == arr2).all(), 'arrays not equal'

    for compression in ['none', 'lzw', 'deflate']:
        for sampleformat in ['int', 'uint', 'float']:
            for bitspersample in [256, 128, 64, 32, 16, 8]:
                if sampleformat == 'float' and (
                                bitspersample < 32 or bitspersample > 128):
                    continue
                if sampleformat in ['int', 'uint'] and bitspersample > 64:
                    continue
                # print compression, sampleformat, bitspersample
                tiff.copy('/tmp/libtiff_test_copy2.tiff',
                          compression=compression,
                          imagedescription='hoo',
                          sampleformat=sampleformat,
                          bitspersample=bitspersample)
                tiff2 = TIFF.open('/tmp/libtiff_test_copy2.tiff', mode='r')
                arr3 = tiff2.read_image()
                assert (arr == arr3).all(), 'arrays not equal %r' % (
                    (compression, sampleformat, bitspersample),)
    print('test copy ok')


if __name__ == '__main__':
    _test_custom_tags()
    _test_tile_write()
    _test_tile_read()
    _test_tags_write()
    _test_tags_read()
    _test_write_float()
    _test_write()
    _test_read()
    _test_copy()

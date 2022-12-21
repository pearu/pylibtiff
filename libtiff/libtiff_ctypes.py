#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

Homepage:  http://pylibtiff.googlecode.com/
"""
# flake8: noqa for F821

from __future__ import print_function
import os
import sys
import numpy as np
import ctypes
import ctypes.util
import struct
import collections

__all__ = ['libtiff', 'TIFF']

cwd = os.getcwd()
try:
    os.chdir(os.path.dirname(__file__))
    if os.name == 'nt':
        # assume that the directory of the libtiff DLL is in PATH.
        for lib in ('tiff', 'libtiff', 'libtiff3'):
            lib = ctypes.util.find_library(lib)
            if lib is not None:
                break
        else:
            # try default installation path:
            lib = r'C:\Program Files\GnuWin32\bin\libtiff3.dll'
            if os.path.isfile(lib):
                print('You should add %r to PATH environment'
                      ' variable and reboot.'
                      % (os.path.dirname(lib)))
            else:
                lib = None
    else:
        if hasattr(sys, 'frozen') and sys.platform == 'darwin' and \
                os.path.exists('../Frameworks/libtiff.dylib'):
            # py2app support, see Issue 8.
            lib = '../Frameworks/libtiff.dylib'
        else:
            lib = ctypes.util.find_library('tiff')

    libtiff = None if lib is None else ctypes.cdll.LoadLibrary(lib)
    if libtiff is None:
        try:
            if sys.platform == "darwin":
                libtiff = ctypes.cdll.LoadLibrary("libtiff.dylib")
            elif "win" in sys.platform:
                libtiff = ctypes.cdll.LoadLibrary("libtiff.dll")
            else:
                libtiff = ctypes.cdll.LoadLibrary("libtiff.so")
        except OSError:
            raise ImportError('Failed to find TIFF library. Make sure that'
                              ' libtiff is installed and its location is'
                              ' listed in PATH|LD_LIBRARY_PATH|..')
finally:
    os.chdir(cwd)

libtiff.TIFFGetVersion.restype = ctypes.c_char_p
libtiff.TIFFGetVersion.argtypes = []

libtiff_version_str = libtiff.TIFFGetVersion()
i = libtiff_version_str.lower().split().index(b'version')
assert i != -1, repr(libtiff_version_str.decode())
libtiff_version = libtiff_version_str.split()[i + 1].decode()
libtiff_version_tuple = tuple(int(i) for i in libtiff_version.split('.'))

tiff_h_name = 'tiff_h_%s' % (libtiff_version.replace('.', '_'))
try:
    exec(u"import libtiff.{0:s} as tiff_h".format(tiff_h_name))
except ImportError:
    tiff_h = None


def _generate_lines_without_continuations(file_obj):
    """Parse lines from tiff.h but concatenate lines using a backslahs for continuation."""
    line_iter = iter(file_obj)
    for header_line in line_iter:
        while header_line.endswith("\\\n"):
            # line continuation - replace '<extra space>\<NL><indentation>' with a single space
            header_line = header_line[:-2].rstrip() + " " + next(line_iter).lstrip()
        yield header_line


if tiff_h is None:
    # WARNING: there is not guarantee that the tiff.h found below will
    # correspond to libtiff version. Although, for clean distros the
    # probability is high.

    include_tiff_h = os.path.join(os.path.split(lib)[0], '..', 'include',
                                  'tiff.h')
    if not os.path.isfile(include_tiff_h):
        include_tiff_h = os.environ.get('TIFF_HEADER_PATH', include_tiff_h)
    if not os.path.isfile(include_tiff_h):
        include_tiff_h = os.path.join(os.path.split(lib)[0], 'include',
                                      'tiff.h')
    if not os.path.isfile(include_tiff_h):
        # fix me for windows:
        include_tiff_h = os.path.join(sys.prefix, 'include', 'tiff.h')
        # print(include_tiff_h)
    if not os.path.isfile(include_tiff_h):
        import glob
        include_tiff_h = (glob.glob(os.path.join(sys.prefix, 'include',
                                                 '*linux*', 'tiff.h')) +
                          glob.glob(os.path.join(sys.prefix, 'include',
                                                 '*kfreebsd*', 'tiff.h')) +
                          [include_tiff_h])[0]
    if not os.path.isfile(include_tiff_h):
        # Base it off of the python called
        include_tiff_h = os.path.realpath(os.path.join(os.path.split(
            sys.executable)[0], '..', 'include', 'tiff.h'))
    if not os.path.isfile(include_tiff_h):
        raise ValueError('Failed to find TIFF header file (may be need to '
                         'run: sudo apt-get install libtiff5-dev)')
    # Read TIFFTAG_* constants for the header file:
    f = open(include_tiff_h, 'r')
    lst = []
    d = {}
    for line in _generate_lines_without_continuations(f):
        if not line.startswith('#define'):
            continue
        words = line[7:].lstrip().split()
        if len(words) > 2:
            words[1] = ''.join(words[1:])
            del words[2:]
        if len(words) != 2:
            continue
        name, value = words
        if name in ['TIFF_GCC_DEPRECATED', 'TIFF_MSC_DEPRECATED']:
            continue
        i = value.find('/*')
        if i != -1:
            value = value[:i]
        if value in d:
            value = d[value]
        else:
            try:
                value = eval(value)
            except Exception as msg:
                print(repr((value, line)), msg)
                raise
        d[name] = value
        lst.append('%s = %s' % (name, value))
    f.close()

    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      tiff_h_name + '.py')
    print('Generating %r from %r' % (fn, include_tiff_h))
    f = open(fn, 'w')
    f.write('\n'.join(lst) + '\n')
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
class c_ttag_t(ctypes.c_uint32):
    pass


if libtiff_version_tuple[:2] >= (4, 5):
    c_tdir_t_base = ctypes.c_uint32
else:
    c_tdir_t_base = ctypes.c_uint16

class c_tdir_t(c_tdir_t_base):
    pass


class c_tsample_t(ctypes.c_uint16):
    pass


class c_tstrip_t(ctypes.c_uint32):
    pass


class c_ttile_t(ctypes.c_uint32):
    pass


class c_tsize_t(ctypes.c_ssize_t):
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
    # TIFFTAG_FAXFILLFUNC             1      TIFFFaxFillFunc* G3/G4
    #                                                         compression
    #                                                         pseudo-tag
    # TIFFTAG_JPEGTABLES              2      u_short*,void**  count & tables
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
    # Contrarily to the libtiff documentation, in libtiff 4.0, the
    # SubIFD array is always 64-bits
    TIFFTAG_SUBIFD: (
        (ctypes.c_uint16, ctypes.c_uint64),
        lambda d: d[1][:d[0]]),  # uint16*, uint64**  count & IFD arrays
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
    TIFFTAG_EXTRASAMPLES: (
        (ctypes.c_uint16, ctypes.c_uint16),
        lambda d: d[1][:d[0]]),  # uint16*, uint16**  count & types array
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
        try:
            try:
                # Python3: it needs bytes for the arguments of type "c_char_p"
                filename = os.fsencode(filename)  # no-op if already bytes
            except AttributeError:
                # Python2: it needs str for the arguments of type "c_char_p"
                if isinstance(filename, unicode):  # noqa: F821
                    filename = filename.encode(sys.getfilesystemencoding())
        except Exception as ex:
            # It's probably going to not work, but let it try
            print('Warning: filename argument is of wrong type or encoding: %s'
                  % ex)

        tiff = libtiff.TIFFOpen(filename, mode.encode('ascii'))
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
        """ Read image from TIFF and return it as an array. """
        if self.IsTiled():
            bits = self.GetField('BitsPerSample')
            sample_format = self.GetField('SampleFormat')
            typ = self.get_numpy_type(bits, sample_format)
            return self.read_tiles(typ)
        else:
            width = self.GetField('ImageWidth')
            height = self.GetField('ImageLength')
            samples_pp = self.GetField(
                'SamplesPerPixel')  # this number includes extra samples
            if samples_pp is None:  # default is 1
                samples_pp = 1
            # Note: In the TIFF specification, BitsPerSample and
            # SampleFormat are per samples. However, libtiff doesn't
            # support mixed format, so it will always return just one
            # value (or raise an error).
            bits = self.GetField('BitsPerSample')
            sample_format = self.GetField('SampleFormat')
            planar_config = self.GetField('PlanarConfig')
            if planar_config is None:  # default is contig
                planar_config = PLANARCONFIG_CONTIG
            compression = self.GetField('Compression')
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
                    raise IOError("Unexpected PlanarConfig = %d"
                                  % planar_config)
            size = arr.nbytes
            data = arr.ctypes.data  # Saves a little bit of time in the loop
            pos = 0
            for strip in range(self.NumberOfStrips()):
                elem = self.ReadEncodedStrip(strip, data + pos, max(size - pos, 0))
                if elem <= 0:
                    raise IOError("Failed to read strip")
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
        elif arr.dtype in np.sctypes['uint'] + [np.bool_]:
            sample_format = SAMPLEFORMAT_UINT
        elif arr.dtype in np.sctypes['int']:
            sample_format = SAMPLEFORMAT_INT
        elif arr.dtype in np.sctypes['complex']:
            sample_format = SAMPLEFORMAT_COMPLEXIEEEFP
        else:
            raise NotImplementedError(repr(arr.dtype))
        shape = arr.shape
        bits = arr.itemsize * 8

        self.SetField(TIFFTAG_COMPRESSION, compression)
        if compression == COMPRESSION_LZW and sample_format in \
                [SAMPLEFORMAT_INT, SAMPLEFORMAT_UINT]:
            # This field can only be set after compression and before
            # writing data. Horizontal predictor often improves compression,
            # but some rare readers might support LZW only without predictor.
            self.SetField(TIFFTAG_PREDICTOR, PREDICTOR_HORIZONTAL)

        self.SetField(TIFFTAG_BITSPERSAMPLE, bits)
        self.SetField(TIFFTAG_SAMPLEFORMAT, sample_format)
        self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT)

        if len(shape) == 1:
            shape = (shape[0], 1)  # Same as 2D with height == 1

        if len(shape) == 2:
            height, width = shape
            size = width * height * arr.itemsize

            self.SetField(TIFFTAG_IMAGEWIDTH, width)
            self.SetField(TIFFTAG_IMAGELENGTH, height)
            self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
            self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
            self.WriteEncodedStrip(0, arr.ctypes.data, size)
            self.WriteDirectory()

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

                self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB)
                self.SetField(TIFFTAG_IMAGEWIDTH, width)
                self.SetField(TIFFTAG_IMAGELENGTH, height)
                self.SetField(TIFFTAG_SAMPLESPERPIXEL, depth)
                self.SetField(TIFFTAG_PLANARCONFIG, planar_config)
                if depth == 4:  # RGBA
                    self.SetField(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNASSALPHA])
                elif depth > 4:  # No idea...
                    self.SetField(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNSPECIFIED] * (depth - 3))

                if planar_config == PLANARCONFIG_CONTIG:
                    self.WriteEncodedStrip(0, arr.ctypes.data, size)
                else:
                    for _n in range(depth):
                        self.WriteEncodedStrip(_n, arr[_n, :, :].ctypes.data, size)
                self.WriteDirectory()
            else:
                depth, height, width = shape
                size = width * height * arr.itemsize
                for _n in range(depth):
                    self.SetField(TIFFTAG_IMAGEWIDTH, width)
                    self.SetField(TIFFTAG_IMAGELENGTH, height)
                    self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
                    self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)

                    self.WriteEncodedStrip(0, arr[_n].ctypes.data, size)
                    self.WriteDirectory()
        else:
            raise NotImplementedError(repr(shape))

    def write_tiles(self, arr, tile_width=None, tile_height=None,
                    compression=None, write_rgb=False):
        compression = self._fix_compression(compression)

        if arr.dtype in np.sctypes['float']:
            sample_format = SAMPLEFORMAT_IEEEFP
        elif arr.dtype in np.sctypes['uint'] + [np.bool_]:
            sample_format = SAMPLEFORMAT_UINT
        elif arr.dtype in np.sctypes['int']:
            sample_format = SAMPLEFORMAT_INT
        elif arr.dtype in np.sctypes['complex']:
            sample_format = SAMPLEFORMAT_COMPLEXIEEEFP
        else:
            raise NotImplementedError(repr(arr.dtype))
        shape = arr.shape
        bits = arr.itemsize * 8

        # if the dimensions are not set, get the values from the tags
        if not tile_width:
            tile_width = self.GetField("TileWidth")
        if not tile_height:
            tile_height = self.GetField("TileLength")

        if tile_width is None or tile_height is None:
            raise ValueError("TileWidth and TileLength must be specified")

        self.SetField(TIFFTAG_COMPRESSION, compression)
        if compression == COMPRESSION_LZW and sample_format in \
                [SAMPLEFORMAT_INT, SAMPLEFORMAT_UINT]:
            # This field can only be set after compression and before
            # writing data. Horizontal predictor often improves compression,
            # but some rare readers might support LZW only without predictor.
            self.SetField(TIFFTAG_PREDICTOR, PREDICTOR_HORIZONTAL)

        self.SetField(TIFFTAG_BITSPERSAMPLE, bits)
        self.SetField(TIFFTAG_SAMPLEFORMAT, sample_format)
        self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT)
        self.SetField(TIFFTAG_TILEWIDTH, tile_width)
        self.SetField(TIFFTAG_TILELENGTH, tile_height)

        total_written_bytes = 0
        if len(shape) == 1:
            shape = (shape[0], 1)  # Same as 2D with height == 1

        def write_plane(arr, tile_arr, width, height,
                        plane_index=0, depth_index=0):
            """ Write all tiles of one plane
            """
            written_bytes = 0
            tile_arr = np.ascontiguousarray(tile_arr)
            # Rows
            for y in range(0, height, tile_height):
                # Cols
                for x in range(0, width, tile_width):
                    # If we are over the edge of the image, use 0 as fill
                    tile_arr[:] = 0

                    # if the tile is on the edge, it is smaller
                    this_tile_width = min(tile_width, width - x)
                    this_tile_height = min(tile_height, height - y)

                    tile_arr[:this_tile_height, :this_tile_width] = \
                        arr[y:y + this_tile_height, x:x + this_tile_width]

                    r = self.WriteTile(tile_arr.ctypes.data, x, y,
                                       depth_index, plane_index)
                    written_bytes += r.value

            return written_bytes

        if len(shape) == 2:
            height, width = shape

            self.SetField(TIFFTAG_IMAGEWIDTH, width)
            self.SetField(TIFFTAG_IMAGELENGTH, height)
            self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
            self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)

            # if there's only one sample per pixel, there is only one plane
            tile_arr = np.zeros((tile_height, tile_width), dtype=arr.dtype)
            total_written_bytes = write_plane(arr, tile_arr, width, height)
            self.WriteDirectory()
        elif len(shape) == 3:
            if write_rgb:
                # Guess the planar config, with preference for separate planes
                if shape[2] == 3 or shape[2] == 4:
                    planar_config = PLANARCONFIG_CONTIG
                    height, width, depth = shape
                else:
                    planar_config = PLANARCONFIG_SEPARATE
                    depth, height, width = shape

                self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB)
                self.SetField(TIFFTAG_IMAGEWIDTH, width)
                self.SetField(TIFFTAG_IMAGELENGTH, height)
                self.SetField(TIFFTAG_SAMPLESPERPIXEL, depth)
                self.SetField(TIFFTAG_PLANARCONFIG, planar_config)
                if depth == 4:  # RGBA
                    self.SetField(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNASSALPHA],
                                  count=1)
                elif depth > 4:  # No idea...
                    self.SetField(TIFFTAG_EXTRASAMPLES,
                                  [EXTRASAMPLE_UNSPECIFIED] * (depth - 3),
                                  count=(depth - 3))

                if planar_config == PLANARCONFIG_CONTIG:
                    # if there is more than one sample per pixel and
                    # it's contiguous in memory, there is only one
                    # plane
                    tile_arr = np.zeros((tile_height, tile_width, depth),
                                        dtype=arr.dtype)
                    total_written_bytes = write_plane(arr, tile_arr,
                                                      width, height)
                else:
                    # multiple samples per pixel, each sample in one plane
                    tile_arr = np.zeros((tile_height, tile_width),
                                        dtype=arr.dtype)
                    for plane_index in range(depth):
                        total_written_bytes += \
                            write_plane(arr[plane_index], tile_arr,
                                        width, height, plane_index)

                self.WriteDirectory()
            else:
                depth, height, width = shape
                self.SetField(TIFFTAG_IMAGEWIDTH, width)
                self.SetField(TIFFTAG_IMAGELENGTH, height)
                self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
                self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
                self.SetField(TIFFTAG_IMAGEDEPTH, depth)
                for depth_index in range(depth):
                    # if there's only one sample per pixel, there is
                    # only one plane
                    tile_arr = np.zeros((tile_height, tile_width),
                                        dtype=arr.dtype)
                    total_written_bytes += write_plane(arr[depth_index],
                                                       tile_arr, width, height,
                                                       0, depth_index)
                self.WriteDirectory()
        else:
            raise NotImplementedError(repr(shape))

        return total_written_bytes

    def read_one_tile(self, x, y):
        """Reads one tile from the TIFF image

        Parameters
        ----------
        x: int
            X coordinate of a pixel inside the desired tile
        y: int
            Y coordinate of a pixel inside the desired tile

        Returns
        -------
        numpy.array
            If there's only one sample per pixel, it returns a numpy
            array with 2 dimensions (x, y)

            If the image has more than one sample per pixel
            (SamplesPerPixel > 1), it will return a numpy array with 3
            dimensions. If PlanarConfig == PLANARCONFIG_CONTIG, the
            returned dimensions will be (x, y, sample_index).

            If PlanarConfig == PLANARCONFIG_SEPARATE, the returned
            dimensions will be (sample_index, x, y).
        """

        num_tcols = self.GetField("TileWidth")
        if num_tcols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to read tiles")
        num_trows = self.GetField("TileLength")
        if num_trows is None:
            num_trows = 1
        num_irows = self.GetField("ImageLength")
        if num_irows is None:
            num_irows = 1
        num_icols = self.GetField("ImageWidth")
        if num_icols is None:
            raise ValueError("TIFFTAG_IMAGEWIDTH must be set to read tiles")
        # this number includes extra samples
        samples_pp = self.GetField('SamplesPerPixel')
        if samples_pp is None:  # default is 1
            samples_pp = 1
        planar_config = self.GetField('PlanarConfig')
        if planar_config is None:  # default is contig
            planar_config = PLANARCONFIG_CONTIG
        num_idepth = self.GetField("ImageDepth")
        if num_idepth is None:
            num_idepth = 1
        bits = self.GetField('BitsPerSample')
        sample_format = self.GetField('SampleFormat')

        # TODO: might need special support if bits < 8
        dtype = self.get_numpy_type(bits, sample_format)

        if y < 0 or y >= num_irows:
            raise ValueError("Invalid y value")
        if x < 0 or x >= num_icols:
            raise ValueError("Invalid x value")

        # make x and y be a multiple of TileWidth and TileLength,
        # and be compatible with ReadTile
        x -= x % num_tcols
        y -= y % num_trows

        # if the tile is in the border, its size should be smaller
        this_tile_height = min(num_trows, num_irows - y)
        this_tile_width = min(num_tcols, num_icols - x)

        def read_plane(tile_plane, plane_index=0, depth_index=0):
            """Read one plane from TIFF.

            The TIFF has more than one plane only if it has more than
            one sample per pixel, and planar_config ==
            PLANARCONFIG_SEPARATE
            """
            # the numpy array should be contigous in memory before
            # calling ReadTile
            tile_plane = np.ascontiguousarray(tile_plane)
            # even if the tile is on the edge, and the final size will
            # be smaller, the size of the array passed to the ReadTile
            # function must be (num_tcols, num_trows)
            #
            # The image has only one depth (ImageDepth == 1), so
            # the z parameter is not read
            r = self.ReadTile(tile_plane.ctypes.data, x, y,
                              depth_index, plane_index)
            if not r:
                raise ValueError(
                    "Could not read tile x:%d,y:%d,z:%d,sample:%d from file" %
                    (x, y, depth_index, plane_index))

            # check if the tile is on the edge of the image
            if this_tile_height < num_trows or this_tile_width < num_tcols:
                # if the tile is on the edge of the image, generate a
                # smaller tile
                tile_plane = tile_plane[:this_tile_height, :this_tile_width]

            return tile_plane

        if num_idepth == 1:
            if samples_pp == 1:
                # the tile plane has always the size of a full tile
                tile_plane = np.zeros((num_trows, num_tcols), dtype=dtype)
                # this tile may be smaller than tile_plane
                tile = read_plane(tile_plane)
            else:
                if planar_config == PLANARCONFIG_CONTIG:
                    # the tile plane has always the size of a full tile
                    tile_plane = np.empty((num_trows, num_tcols, samples_pp),
                                          dtype=dtype)
                    # this tile may be smaller than tile_plane,
                    # if the tile is on the edge of the image
                    tile = read_plane(tile_plane)
                else:
                    # the tile plane has always the size of a full tile
                    tile_plane = np.empty((samples_pp, num_trows, num_tcols),
                                          dtype=dtype)
                    # this tile may be smaller than tile_plane,
                    # if the tile is on the edge of the image
                    tile = np.empty((samples_pp, this_tile_height,
                                     this_tile_width), dtype=dtype)
                    for plane_index in range(samples_pp):
                        tile[plane_index] = read_plane(
                            tile_plane[plane_index], plane_index)

        else:
            if samples_pp > 1:
                raise NotImplementedError(
                    "ImageDepth > 1 and SamplesPerPixel > 1 not implemented")

            # the tile plane has always the size of a full tile
            tile_plane = np.zeros((num_idepth, num_trows, num_tcols),
                                  dtype=dtype)
            # this tile may be smaller than tile_plane,
            # if the tile is on the edge of the image
            tile = np.empty((num_idepth, this_tile_height, this_tile_width),
                            dtype=dtype)
            for depth_index in range(num_idepth):
                # As samples_pp == 1, there's only one plane, so the z
                # parameter is not read
                tile[depth_index] = read_plane(
                    tile_plane[depth_index], 0, depth_index)

        return tile

    def read_tiles(self, dtype=np.uint8):
        num_tcols = self.GetField("TileWidth")
        if num_tcols is None:
            raise ValueError("TIFFTAG_TILEWIDTH must be set to read tiles")
        num_trows = self.GetField("TileLength")
        if num_trows is None:
            raise ValueError("TIFFTAG_TILELENGTH must be set to read tiles")
        num_icols = self.GetField("ImageWidth")
        if num_icols is None:
            raise ValueError("TIFFTAG_IMAGEWIDTH must be set to read tiles")
        num_irows = self.GetField("ImageLength")
        if num_irows is None:
            num_irows = 1
        num_depths = self.GetField("ImageDepth")
        if num_depths is None:
            num_depths = 1
        # this number includes extra samples
        samples_pp = self.GetField('SamplesPerPixel')
        if samples_pp is None:  # default is 1
            samples_pp = 1
        planar_config = self.GetField('PlanarConfig')
        if planar_config is None:  # default is contig
            planar_config = PLANARCONFIG_CONTIG

        def read_plane(plane, tmp_tile, plane_index=0, depth_index=0):
            for y in range(0, num_irows, num_trows):
                for x in range(0, num_icols, num_tcols):
                    r = self.ReadTile(tmp_tile.ctypes.data, x, y,
                                      depth_index, plane_index)
                    if not r:
                        raise ValueError(
                            "Could not read tile x:%d,y:%d,z:%d,sample:%d"
                            " from file" %
                            (x, y, plane_index, depth_index))

                    # if the tile is on the edge, it is smaller
                    tile_width = min(num_tcols, num_icols - x)
                    tile_height = min(num_trows, num_irows - y)

                    plane[y:y + tile_height, x:x + tile_width] = \
                        tmp_tile[:tile_height, :tile_width]

        if samples_pp == 1:
            if num_depths == 1:
                # if there's only one sample per pixel there is only
                # one plane
                full_image = np.empty((num_irows, num_icols),
                                      dtype=dtype, order='C')
                tmp_tile = np.empty((num_trows, num_tcols),
                                    dtype=dtype, order='C')
                read_plane(full_image, tmp_tile)
            else:
                full_image = np.empty((num_depths, num_irows, num_icols),
                                      dtype=dtype, order='C')
                tmp_tile = np.empty((num_trows, num_tcols),
                                    dtype=dtype, order='C')
                for depth_index in range(num_depths):
                    read_plane(full_image[depth_index], tmp_tile, 0,
                               depth_index)
        else:
            if planar_config == PLANARCONFIG_CONTIG:
                # if there is more than one sample per pixel and it's
                # contiguous in memory, there is only one plane
                full_image = np.empty((num_irows, num_icols, samples_pp),
                                      dtype=dtype, order='C')
                tmp_tile = np.empty((num_trows, num_tcols, samples_pp),
                                    dtype=dtype, order='C')
                read_plane(full_image, tmp_tile)
            elif planar_config == PLANARCONFIG_SEPARATE:
                # multiple samples per pixel, each sample in one plane
                full_image = np.empty((samples_pp, num_irows, num_icols),
                                      dtype=dtype, order='C')
                tmp_tile = np.empty((num_trows, num_tcols),
                                    dtype=dtype, order='C')
                for plane_index in range(samples_pp):
                    read_plane(full_image[plane_index], tmp_tile, plane_index)
            else:
                raise IOError("Unexpected PlanarConfig = %d" % planar_config)

        return full_image

    def iter_images(self, verbose=False):
        """ Iterator of all images in a TIFF file.
        """
        yield self.read_image(verbose=verbose)
        while not self.LastDirectory():
            self.ReadDirectory()
            yield self.read_image(verbose=verbose)
        self.SetDirectory(0)

    def __del__(self):
        self.close()

    @debug
    def FileName(self):
        return libtiff.TIFFFileName(self)
    filename = FileName

    @debug
    def CurrentRow(self):
        return libtiff.TIFFCurrentRow(self)
    currentrow = CurrentRow

    @debug
    def CurrentStrip(self):
        return libtiff.TIFFCurrentStrip(self)
    currentstrip = CurrentStrip

    @debug
    def CurrentTile(self):
        return libtiff.TIFFCurrentTile(self)
    currenttile = CurrentTile

    @debug
    def CurrentDirectory(self):
        return libtiff.TIFFCurrentDirectory(self)
    currentdirectory = CurrentDirectory

    @debug
    def LastDirectory(self):
        return libtiff.TIFFLastDirectory(self)
    lastdirectory = LastDirectory

    @debug
    def ReadDirectory(self):
        return libtiff.TIFFReadDirectory(self)
    readdirectory = ReadDirectory

    @debug
    def WriteDirectory(self):
        r = libtiff.TIFFWriteDirectory(self)
        assert r == 1, repr(r)
    writedirectory = WriteDirectory

    @debug
    def SetDirectory(self, dirnum):
        return libtiff.TIFFSetDirectory(self, dirnum)
    setdirectory = SetDirectory

    @debug
    def SetSubDirectory(self, diroff):
        """
        Changes the current directory
        and reads its contents with TIFFReadDirectory.
        The parameter dirnum specifies the subfile/directory as
        an integer number, with the first directory numbered zero.

        SetSubDirectory acts like SetDirectory,
        except the directory is specified as a file offset instead of an index;
        this is required for accessing subdirectories
        linked through a SubIFD tag.

        Parameters
        ----------
        diroff: int
            The offset of the subimage. It's important to notice that
            it is not an index, like dirnum on SetDirectory

        Returns
        -------
        int
            On successful return 1 is returned.
            Otherwise, 0 is returned if dirnum or diroff
            specifies a non-existent directory,
            or if an error was encountered
            while reading the directory's contents.
        """
        return libtiff.TIFFSetSubDirectory(self, diroff)

    @debug
    def Fileno(self):
        return libtiff.TIFFFileno(self)
    fileno = Fileno

    @debug
    def GetMode(self):
        return libtiff.TIFFGetMode(self)
    getmode = GetMode

    @debug
    def IsTiled(self):
        return libtiff.TIFFIsTiled(self)
    istiled = IsTiled

    @debug
    def IsByteSwapped(self):
        return libtiff.TIFFIsByteSwapped(self)
    isbyteswapped = IsByteSwapped

    @debug
    def IsUpSampled(self):
        return libtiff.TIFFIsUpSampled(self)
    isupsampled = IsUpSampled

    # noinspection PyPep8Naming
    @debug
    def isMSB2LSB(self):
        return libtiff.TIFFIsMSB2LSB(self)

    @debug
    def NumberOfStrips(self):
        return libtiff.TIFFNumberOfStrips(self).value
    numberofstrips = NumberOfStrips

    @debug
    def WriteScanline(self, buf, row, sample=0):
        return libtiff.TIFFWriteScanline(self, buf, row, sample)
    writescanline = WriteScanline

    @debug
    def ReadScanline(self, buf, row, sample=0):
        return libtiff.TIFFReadScanline(self, buf, row, sample)
    readscanline = ReadScanline

    def ScanlineSize(self):
        return libtiff.TIFFScanlineSize(self).value
    scanlinesize = ScanlineSize

    # @debug
    def ReadRawStrip(self, strip, buf, size):
        return libtiff.TIFFReadRawStrip(self, strip, buf, size).value
    readrawstrip = ReadRawStrip

    def ReadEncodedStrip(self, strip, buf, size):
        return libtiff.TIFFReadEncodedStrip(self, strip, buf, size).value
    readencodedstrip = ReadEncodedStrip

    def StripSize(self):
        return libtiff.TIFFStripSize(self).value
    stripsize = StripSize

    def RawStripSize(self, strip):
        return libtiff.TIFFRawStripSize(self, strip).value
    rawstripsize = RawStripSize

    @debug
    def WriteRawStrip(self, strip, buf, size):
        r = libtiff.TIFFWriteRawStrip(self, strip, buf, size)
        assert r.value == size, repr((r.value, size))
    writerawstrip = WriteRawStrip

    @debug
    def WriteEncodedStrip(self, strip, buf, size):
        r = libtiff.TIFFWriteEncodedStrip(self, strip, buf, size)
        assert r.value == size, repr((r.value, size))
    writeencodedstrip = WriteEncodedStrip

    @debug
    def ReadTile(self, buf, x, y, z, sample):
        """ Read and decode a tile of data from an open TIFF file

        Parameters
        ----------
        buf: array
            Content read from the tile.
            The buffer must be large enough to hold an entire tile of data.
            Applications should call the routine TIFFTileSize
            to find out the size (in bytes) of a tile buffer.
        x: int
            X coordinate of the upper left pixel of the tile.
            It must be a multiple of TileWidth.
        y: int
            Y coordinate of the upper left pixel of the tile.
            It must be a multiple of TileLength.
        z: int
            It is used if the image is deeper than 1 slice (ImageDepth>1)
        sample: integer
            It is used only if data are organized
            in separate planes (PlanarConfiguration=2)

        Returns
        -------
        int
            -1 if it detects an error;
            otherwise the number of bytes in the decoded tile is returned.
        """
        return libtiff.TIFFReadTile(self, buf, x, y, z, sample)

    @debug
    def WriteTile(self, buf, x, y, z, sample):
        """ TIFFWriteTile - encode and write a tile of data to an open TIFF file

        Parameters
        ----------
        arr: array
            Content to be written to the tile.
            The buffer must be contain an entire tile of data.
            Applications should call the routine TIFFTileSize
            to find out the size (in bytes) of a tile buffer.
        x: int
            X coordinate of the upper left pixel of the tile.
            It must be a multiple of TileWidth.
        y: int
            Y coordinate of the upper left pixel of the tile.
            It must be a multiple of TileLength.
        z: int
            It is used if the image is deeper than 1 slice (ImageDepth>1)
        sample: integer
            It is used only if data are organized
            in separate planes (PlanarConfiguration=2)

        Returns
        -------
        int
            -1 if it detects an error;
            otherwise the number of bytes in the tile is returned.
        """
        r = libtiff.TIFFWriteTile(self, buf, x, y, z, sample)
        assert r.value >= 0, repr(r.value)
        return r

    closed = False

    def close(self, _libtiff=libtiff):
        if not self.closed and self.value is not None:
            _libtiff.TIFFClose(self)
            self.closed = True
        return

    # def (self): return libtiff.TIFF(self)

    @debug
    def GetField(self, tag, ignore_undefined_tag=True, count=None):
        """ Return TIFF field _value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """
        if tag in ['PixelSizeX', 'PixelSizeY', 'RelativeTime']:
            descr = self.GetField('ImageDescription')
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
            bps = self.GetField("BitsPerSample")
            if bps is None:
                print(
                    "Warning: BitsPerSample is required to get ColorMap, "
                    "assuming 8 bps...")
                bps = 8
            elif bps > 16:
                # There is no way to check whether a field is present without
                # passing all the arguments. With more than 16 bits, it'd be a
                # lot of memory needed (and COLORMAP is very unlikely).
                print("Not trying to read COLORMAP tag with %d bits" % (bps,))
                return None

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
            r = libtiff.TIFFGetField(self, c_ttag_t(tag), rdata_ptr, gdata_ptr,
                                     bdata_ptr)
            data = (rdata, gdata, bdata)
        elif isinstance(data_type, tuple):
            # Variable length array, with the length as first value
            count_type, data_type = data_type
            count = count_type()
            pdt = ctypes.POINTER(data_type)
            vldata = pdt()
            r = libtiff.TIFFGetField(self, c_ttag_t(tag), ctypes.byref(count),
                                     ctypes.byref(vldata))
            data = (count.value, vldata)
        else:
            if issubclass(data_type, ctypes.Array):
                pdt = ctypes.POINTER(data_type)
                data = pdt()
            else:
                data = data_type()

            if count is None:
                r = libtiff.TIFFGetField(self, c_ttag_t(tag),
                                         ctypes.byref(data))
            else:
                # TODO: is this ever used? Is there any tag that is
                # accessed like that?
                r = libtiff.TIFFGetField(self, c_ttag_t(tag),
                                         count, ctypes.byref(data))
        if not r:  # tag not defined for current directory
            if not ignore_undefined_tag:
                print(
                    'Warning: tag %r not defined in currect directory' % tag)
            return None

        return convert(data)

    # @debug
    def SetField(self, tag, _value, count=None):
        """ Set TIFF field _value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """
        if count is not None:
            print("Warning: count argument is deprecated")

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

            bps = self.GetField("BitsPerSample")
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
            r = libtiff.TIFFSetField(self, c_ttag_t(tag), r_ptr, g_ptr, b_ptr)
        else:
            count_type = None
            if isinstance(data_type, tuple):
                # Variable length => count + data_type of array
                count_type, data_type = data_type
                count = len(_value)
                data_type = data_type * count  # make it an array

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

            if count_type is None:
                r = libtiff.TIFFSetField(self, c_ttag_t(tag), data)
            else:
                r = libtiff.TIFFSetField(self, c_ttag_t(tag), count, data)
        return r

    def info(self):
        """ Return a string containing <tag name: field value> map.
        """
        _l = ['filename: %s' % (self.FileName())]
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
            v = self.GetField(tagname)
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
        self.SetDirectory(0)
        self.ReadDirectory()
        while 1:
            other.SetDirectory(self.CurrentDirectory())
            bits = self.GetField('BitsPerSample')
            sample_format = self.GetField('SampleFormat')
            assert bits >= 8, repr((bits, sample_format))
            itemsize = bits // 8
            dtype = self.get_numpy_type(bits, sample_format)
            for _name, define in name_define_list:
                orig_value = self.GetField(define)
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
                other.SetField(define, _value)
            new_bits = other.GetField('BitsPerSample')
            new_sample_format = other.GetField('SampleFormat')
            new_dtype = other.get_numpy_type(new_bits, new_sample_format)
            assert new_bits >= 8, repr(
                (new_bits, new_sample_format, new_dtype))
            new_itemsize = new_bits // 8
            strip_size = self.StripSize()
            buf = np.zeros(strip_size // itemsize, dtype)
            for strip in range(self.NumberOfStrips()):
                elem = self.ReadEncodedStrip(strip, buf.ctypes.data,
                                             strip_size)
                if elem > 0:
                    new_buf = buf.astype(new_dtype)
                    other.WriteEncodedStrip(strip, new_buf.ctypes.data,
                                            (elem * new_itemsize) // itemsize)
            self.ReadDirectory()
            if self.LastDirectory():
                break
        other.close()


class TIFF3D(TIFF):
    """subclass of TIFF for handling import of 3D (multi-directory) files.

    like TIFF, but TIFF3D.read_image() will attempt to restore a 3D
    numpy array when given a multi-image TIFF file; performing the
    inverse of

      TIFF_instance.write(numpy.zeros((40, 200, 200)))

    like so:

      arr = TIFF3D_instance.read_image()
      arr.shape # gives (40, 200, 200)

    if you tried this with a normal TIFF instance, you would get this:

      arr = TIFF_instance.read_image()
      arr.shape # gives (200, 200)

    and you would have to loop over each image by hand with
    TIFF.iter_images().

    """

    @classmethod
    def open(cls, filename, mode='r'):
        """ just like TIFF.open, except returns a TIFF3D instance.
        """
        try:
            try:
                # Python3: it needs bytes for the arguments of type "c_char_p"
                filename = os.fsencode(filename)  # no-op if already bytes
            except AttributeError:
                # Python2: it needs str for the arguments of type "c_char_p"
                if isinstance(filename, unicode):  # noqa: F821
                    filename = filename.encode(sys.getfilesystemencoding())
        except Exception as ex:
            # It's probably going to not work, but let it try
            print('Warning: filename argument is of wrong type or encoding: %s'
                  % ex)
        if isinstance(mode, str):
            mode = mode.encode()

        # monkey-patch the restype:
        old_restype = libtiff.TIFFOpen.restype
        libtiff.TIFFOpen.restype = TIFF3D
        try:
            # actually call the library function:
            tiff = libtiff.TIFFOpen(filename, mode)
        except Exception:
            raise
        finally:
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
        width = self.GetField('ImageWidth')
        height = self.GetField('ImageLength')
        bits = self.GetField('BitsPerSample')
        sample_format = self.GetField('SampleFormat')
        compression = self.GetField('Compression')

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
            if self.LastDirectory():
                break
            self.ReadDirectory()
        self.SetDirectory(0)

        # we proceed assuming all directories have the same properties from
        # above.
        layer_size = width * height * itemsize
        # total_size = layer_size * depth
        arr = np.zeros((depth, height, width), typ)

        layer = 0
        while True:
            pos = 0
            elem = None
            datal = arr.ctypes.data + layer * layer_size
            for strip in range(self.NumberOfStrips()):
                if elem is None:
                    elem = self.ReadEncodedStrip(strip, datal + pos, layer_size)
                elif elem:
                    elem = self.ReadEncodedStrip(strip, datal + pos,
                                                 min(layer_size - pos, elem))
                pos += elem
            if self.LastDirectory():
                break
            self.ReadDirectory()
            layer += 1
        self.SetDirectory(0)
        return arr


class CZ_LSMInfo:
    def __init__(self, tiff):
        self.tiff = tiff
        self.filename = tiff.filename()
        self.offset = tiff.GetField(TIFFTAG_CZ_LSMINFO)
        self.extract_info()

    def extract_info(self):
        if self.offset is None:
            return
        _f = libtiff.TIFFFileno(self.tiff)
        fd = os.fdopen(_f, 'r')
        pos = fd.tell()
        self.offset = self.tiff.GetField(TIFFTAG_CZ_LSMINFO)
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

libtiff.TIFFSetSubDirectory.restype = ctypes.c_int
libtiff.TIFFSetSubDirectory.argtypes = [TIFF, ctypes.c_uint64]

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

# GetField and SetField arguments are dependent on the tag
libtiff.TIFFGetField.restype = ctypes.c_int

libtiff.TIFFSetField.restype = ctypes.c_int

libtiff.TIFFNumberOfStrips.restype = c_tstrip_t
libtiff.TIFFNumberOfStrips.argtypes = [TIFF]

libtiff.TIFFWriteScanline.restype = ctypes.c_int
libtiff.TIFFWriteScanline.argtypes = [TIFF, c_tdata_t, ctypes.c_uint32, c_tsample_t]

libtiff.TIFFReadScanline.restype = ctypes.c_int
libtiff.TIFFReadScanline.argtypes = [TIFF, c_tdata_t, ctypes.c_uint32, c_tsample_t]

libtiff.TIFFScanlineSize.restype = c_tsize_t
libtiff.TIFFScanlineSize.argtypes = [TIFF]

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

# For adding custom tags (must be void pointer otherwise callback seg faults)
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

        a.SetField("ARTIST", "MY NAME")
        a.SetField("LibtiffTestByte", 42)
        a.SetField("LibtiffTeststr", "FAKE")
        a.SetField("LibtiffTestuint16", 42)
        a.SetField("LibtiffTestMultiuint32", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
        a.SetField("XPOSITION", 42.0)
        a.SetField("PRIMARYCHROMATICITIES", (1.0, 2, 3, 4, 5, 6))

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
        tmp = a.GetField("XPOSITION")
        assert tmp == 42.0, "XPosition was not read as 42.0"
        tmp = a.GetField("ARTIST")
        assert tmp == "MY NAME", "Artist was not read as 'MY NAME'"
        tmp = a.GetField("LibtiffTestByte")
        assert tmp == 42, "LibtiffTestbyte was not read as 42"
        tmp = a.GetField("LibtiffTestuint16")
        assert tmp == 42, "LibtiffTestuint16 was not read as 42"
        tmp = a.GetField("LibtiffTestMultiuint32")
        assert tmp == [1, 2, 3, 4, 5, 6, 7, 8, 9,
                       10], "LibtiffTestMultiuint32 was not read as [1,2,3," \
                            "4,5,6,7,8,9,10]"
        tmp = a.GetField("LibtiffTeststr")
        assert tmp == "FAKE", "LibtiffTeststr was not read as 'FAKE'"
        tmp = a.GetField("PRIMARYCHROMATICITIES")
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
    # Keep pointer to extender object, no gc:
    test_extender = add_tags(test_tags)  # noqa: F841
    _tag_write()
    _tag_read()


def _test_tile_write():
    a = TIFF.open("/tmp/libtiff_test_tile_write.tiff", "w")

    data_array = np.tile(list(range(500)), (1, 6)).astype(np.uint8)
    a.SetField("TileWidth", 512)
    a.SetField("TileLength", 528)
    # tile_width and tile_height is not set, write_tiles get these values from
    # TileWidth and TileLength tags
    assert a.write_tiles(data_array) == (512 * 528) * 6,\
        "could not write tile images"  # 1D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 2D Arrays
    data_array = np.tile(list(range(500)), (2500, 6)).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528) == (512 * 528) * 5 * 6,\
        "could not write tile images"  # 2D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 3D Arrays, 3rd dimension as last dimension
    data_array = np.array(range(2500 * 3000 * 3)).reshape(
        2500, 3000, 3).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528, None, True) \
        == (512 * 528) * 5 * 6 * 3,\
        "could not write tile images"  # 3D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # 3D Arrays, 3rd dimension as first dimension
    data_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8)
    assert a.write_tiles(data_array, 512, 528, None, True)\
        == (512 * 528) * 5 * 6 * 3,\
        "could not write tile images"  # 3D
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    # Grayscale image with 3 depths
    data_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8)
    written_bytes = a.write_tiles(data_array, 512, 528)
    assert written_bytes == 512 * 528 * 5 * 6 * 3,\
        "could not write tile images, written_bytes: %s" % (written_bytes,)
    print("Tile Write: Wrote array of shape %r" % (data_array.shape,))

    print("Tile Write: SUCCESS")


def _test_tile_read(filename="/tmp/libtiff_test_tile_write.tiff"):
    import sys
    if filename is None:
        if len(sys.argv) != 2:
            print("Run `libtiff.py <filename>` for testing.")
            return
        filename = sys.argv[1]

    a = TIFF.open(filename, "r")

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
        assert field_value == tag['exp_value'],\
            repr((tag['tag'], tag['exp_value'], field_value))

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (1, 3000), "tile data read was the wrong shape"
    test_array = np.array(list(range(500)) * 6).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0,\
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
        assert field_value == tag['exp_value'],\
            repr((tag['tag'], tag['exp_value'], field_value))

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (2500, 3000),\
        "tile data read was the wrong shape"
    test_array = np.tile(list(range(500)),
                         (2500, 6)).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0,\
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
        assert field_value == tag['exp_value'],\
            repr(tag['tag'], tag['exp_value'], field_value)

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (2500, 3000, 3),\
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3)).reshape(
        2500, 3000, 3).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0,\
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
        assert field_value == tag['exp_value'],\
            repr(tag['tag'], tag['exp_value'], field_value)

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (3, 2500, 3000),\
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0,\
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
        assert field_value == tag['exp_value'],\
            repr([tag['tag'], tag['exp_value'], field_value])

    data_array = a.read_tiles()
    print("Tile Read: Read array of shape %r" % (data_array.shape,))
    assert data_array.shape == (3, 2500, 3000),\
        "tile data read was the wrong shape"
    test_array = np.array(range(2500 * 3000 * 3)).reshape(
        3, 2500, 3000).astype(np.uint8).flatten()
    assert np.nonzero(data_array.flatten() != test_array)[0].shape[0] == 0,\
        "tile data read was not the same as the expected data"
    print("Tile Read: Data is the same as expected from tile write test")

    print("Tile Read: SUCCESS")


def _test_read_one_tile():
    filename = "/tmp/libtiff_test_tile_write.tiff"
    tiff = TIFF.open(filename, "r")

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
        assert inst.message == "Invalid x value", repr(inst.message)

    # test y greater than the image height
    try:
        tiff.read_one_tile(0, 5000)
        raise AssertionError(
            "An exception must be raised with invalid (x, y) values")
    except ValueError as inst:
        assert inst.message == "Invalid y value", repr(inst.message)

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


def _test_tiled_image_read(filename="/tmp/libtiff_test_tile_write.tiff"):
    """
    Tests opening a tiled image
    """

    def assert_image_tag(tiff, tag_name, expected_value):
        value = tiff.GetField(tag_name)
        assert value == expected_value,\
            ('%s expected to be %d, but it\'s %d'
             % (tag_name, expected_value, value))

    # _test_tile_write is called here just to make sure that the image
    # is saved, even if the order of the tests changed
    _test_tile_write()
    tiff = TIFF.open(filename, "r")

    # sets the current image to the second image
    tiff.SetDirectory(1)
    # test tag values
    assert_image_tag(tiff, 'ImageWidth', 3000)
    assert_image_tag(tiff, 'ImageLength', 2500)
    assert_image_tag(tiff, 'TileWidth', 512)
    assert_image_tag(tiff, 'TileLength', 528)
    assert_image_tag(tiff, 'BitsPerSample', 8)
    assert_image_tag(tiff, 'Compression', COMPRESSION_NONE)  # noqa: F821

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


def _test_tags_write():
    tiff = TIFF.open('/tmp/libtiff_tags_write.tiff', mode='w')
    tmp = tiff.SetField("Artist", "A Name")
    assert tmp == 1, "Tag 'Artist' was not written properly"
    tmp = tiff.SetField("DocumentName", "")
    assert tmp == 1, "Tag 'DocumentName' with empty string was not written " \
                     "properly"
    tmp = tiff.SetField("PrimaryChromaticities", [1, 2, 3, 4, 5, 6])
    assert tmp == 1, "Tag 'PrimaryChromaticities' was not written properly"
    tmp = tiff.SetField("BitsPerSample", 8)
    assert tmp == 1, "Tag 'BitsPerSample' was not written properly"
    tmp = tiff.SetField("ColorMap", [[x * 256 for x in range(256)]] * 3)
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
    tmp = tiff.GetField("Artist")
    assert tmp == "A Name", "Tag 'Artist' did not read the correct value (" \
        "Got '%s'; Expected 'A Name')" % (tmp,)
    tmp = tiff.GetField("DocumentName")
    assert tmp == "", "Tag 'DocumentName' did not read the correct value (" \
        "Got '%s'; Expected empty string)" % (tmp,)
    tmp = tiff.GetField("PrimaryChromaticities")
    assert tmp == [1, 2, 3, 4, 5,
                   6], "Tag 'PrimaryChromaticities' did not read the " \
                       "correct value (Got '%r'; Expected '[1,2,3,4,5,6]'" % (
        tmp,)
    tmp = tiff.GetField("BitsPerSample")
    assert tmp == 8, "Tag 'BitsPerSample' did not read the correct value (" \
                     "Got %s; Expected 8)" % (str(tmp),)
    tmp = tiff.GetField("ColorMap")
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


def _test_write_rgba():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros((5, 6, 4), np.uint8)
    for i in np.ndindex(*arr.shape):
        arr[i] = 20 * i[0] + 10 * i[1] + i[2]
    print(arr)
    tiff.write_image(arr, write_rgb=True)
    del tiff

    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    arr2 = tiff.read_image()
    print(arr2)

    np.testing.assert_array_equal(arr, arr2)


def _test_tree():
    # Write a TIFF image with the following tree structure:
    # Im0 --SubIFD--> Im0,1 ---> Im0,2 ---> Im0,3
    #  |
    #  V
    # Im1
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
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

    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='r')
    print(tiff.info())
    n = 0
    for im in tiff.iter_images(verbose=True):
        print(im)
        n += 1

    assert n == 2


def _test_copy():
    tiff = TIFF.open('/tmp/libtiff_test_compression.tiff', mode='w')
    arr = np.zeros((5, 6), np.uint32)
    for _i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[_i, j] = 1 + _i + 10 * j
    # from scipy.stats import poisson
    # arr = poisson.rvs (arr)
    tiff.SetField('ImageDescription', 'Hey\nyou')
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
    _test_read_one_tile()
    _test_tiled_image_read()
    _test_tags_write()
    _test_tags_read()
    _test_write_float()
    _test_write_rgba()
    _test_tree()
    _test_write()
    _test_read()
    _test_copy()

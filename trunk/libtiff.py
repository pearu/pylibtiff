#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

"""
__author__ = 'Pearu Peterson'
__date__ = 'April 2009'
__license__ = 'BSD'
__version__ = '0.1-svn'
__all__ = ['libtiff', 'TIFF']

import numpy as np
from numpy import ctypeslib
import ctypes
import ctypes.util

lib = ctypes.util.find_library('tiff')
assert lib, `lib`
libtiff = ctypes.cdll.LoadLibrary(lib)
include_tiff_h = '/usr/include/tiff.h'

# types defined by tiff.h
class c_ttag_t(ctypes.c_uint): pass
class c_tdir_t(ctypes.c_uint16): pass
class c_tsample_t(ctypes.c_uint16): pass
class c_tstrip_t(ctypes.c_uint32): pass
class c_ttile_t(ctypes.c_uint32): pass
class c_tsize_t(ctypes.c_int32): pass
class c_toff_t(ctypes.c_int32): pass
class c_tdata_t(ctypes.c_void_p): pass
class c_thandle_t(ctypes.c_void_p): pass

define_to_name_map = dict(Orientation={}, Compression={},
                          PhotoMetric={}, PlanarConfig={},
                          SampleFormat={}, FillOrder={},
                          FaxMode={}, 
                          )

# Read and initialize TIFFTAG_* constants:
f = open (include_tiff_h, 'r')
for line in f.readlines():
    if not line.startswith('#define'): continue
    words = line[7:].lstrip().split()[:2]
    if len (words)!=2: continue
    name, value = words
    i = value.find('/*')
    if i!=-1: value = value[:i]
    exec '%s = %s' % (name, value)
    for n in define_to_name_map:
        if name.startswith(n.upper()):
            define_to_name_map[n][eval(value)] = name

tifftags = {

#TODO:
#TIFFTAG_COLORMAP                3      uint16**          1<<BitsPerSample arrays
#TIFFTAG_DOTRANGE                2      uint16*
#TIFFTAG_HALFTONEHINTS           2      uint16*
#TIFFTAG_PAGENUMBER              2      uint16*
#TIFFTAG_YCBCRSUBSAMPLING        2      uint16*
#TIFFTAG_EXTRASAMPLES            2      uint16*,uint16**  count & types array
#TIFFTAG_FAXFILLFUNC             1      TIFFFaxFillFunc*  G3/G4 compression pseudo-tag
#TIFFTAG_JPEGTABLES              2      u_short*,void**   count & tables
#TIFFTAG_SUBIFD                  2      uint16*,uint32**  count & offsets array
#TIFFTAG_TRANSFERFUNCTION        1 or 3 uint16**          1<<BitsPerSample entry arrays
#TIFFTAG_ICCPROFILE              2      uint32*,void**    count, profile data

    # TIFFTAG: type, conversion  
    TIFFTAG_ARTIST: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_COPYRIGHT: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_DATETIME: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_DOCUMENTNAME: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_HOSTCOMPUTER: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_IMAGEDESCRIPTION: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_INKNAMES: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_MAKE: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_MODEL: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_PAGENAME: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_SOFTWARE: (ctypes.c_char_p, lambda d:d.value),
    TIFFTAG_TARGETPRINTER: (ctypes.c_char_p, lambda d:d.value),

    TIFFTAG_BADFAXLINES: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_CONSECUTIVEBADFAXLINES: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_GROUP3OPTIONS: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_GROUP4OPTIONS: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_IMAGEDEPTH: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_IMAGEWIDTH: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_IMAGELENGTH: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_ROWSPERSTRIP: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_SUBFILETYPE: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_TILEDEPTH: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_TILELENGTH: (ctypes.c_uint32, lambda d:d.value),
    TIFFTAG_TILEWIDTH: (ctypes.c_uint32, lambda d:d.value),

    TIFFTAG_STRIPBYTECOUNTS: (ctypes.POINTER(ctypes.c_uint32), lambda d:d.contents),
    TIFFTAG_STRIPOFFSETS: (ctypes.POINTER(ctypes.c_uint32), lambda d:d.contents),
    TIFFTAG_TILEBYTECOUNTS: (ctypes.POINTER(ctypes.c_uint32), lambda d:d.contents),
    TIFFTAG_TILEOFFSETS: (ctypes.POINTER(ctypes.c_uint32), lambda d:d.contents),
        
    TIFFTAG_BITSPERSAMPLE: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_CLEANFAXDATA: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_COMPRESSION: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_DATATYPE: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_FILLORDER: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_INKSET: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_MATTEING: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_MAXSAMPLEVALUE: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_MINSAMPLEVALUE: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_ORIENTATION: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_PHOTOMETRIC: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_PLANARCONFIG: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_PREDICTOR: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_RESOLUTIONUNIT: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_SAMPLEFORMAT: (ctypes.c_uint16, lambda d:d.value),
    TIFFTAG_YCBCRPOSITIONING: (ctypes.c_uint16, lambda d:d.value),

    TIFFTAG_JPEGQUALITY: (ctypes.c_int, lambda d:d.value),
    TIFFTAG_JPEGCOLORMODE: (ctypes.c_int, lambda d:d.value),
    TIFFTAG_JPEGTABLESMODE: (ctypes.c_int, lambda d:d.value),
    TIFFTAG_FAXMODE: (ctypes.c_int, lambda d:d.value),

    TIFFTAG_SMAXSAMPLEVALUE: (ctypes.c_double, lambda d:d.value),
    TIFFTAG_SMINSAMPLEVALUE: (ctypes.c_double, lambda d:d.value),

    TIFFTAG_STONITS: (ctypes.POINTER(ctypes.c_double), lambda d:d.contents),

    TIFFTAG_XPOSITION: (ctypes.c_float, lambda d:d.value),
    TIFFTAG_XRESOLUTION: (ctypes.c_float, lambda d:d.value),
    TIFFTAG_YPOSITION: (ctypes.c_float, lambda d:d.value),
    TIFFTAG_YRESOLUTION: (ctypes.c_float, lambda d:d.value),

    TIFFTAG_PRIMARYCHROMATICITIES: (ctypes.POINTER(ctypes.c_float), lambda d:d.contents),
    TIFFTAG_REFERENCEBLACKWHITE: (ctypes.POINTER(ctypes.c_float), lambda d:d.contents),
    TIFFTAG_WHITEPOINT: (ctypes.POINTER(ctypes.c_float), lambda d:d.contents),
    TIFFTAG_YCBCRCOEFFICIENTS: (ctypes.POINTER(ctypes.c_float), lambda d:d.contents),

}

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

    """

    @classmethod
    def open(cls, filename, mode='r'):
        """ Open tiff file as TIFF.
        """
        tiff = libtiff.TIFFOpen(filename, mode)
        if tiff.value is None:
            raise TypeError ('Failed to open file '+`filename`)
        return tiff

    def read_image(self, verbose=False):
        """ Read image from TIFF and return it as an array.
        """
        width = self.GetField('ImageWidth')
        height = self.GetField('ImageLength')
        bits = self.GetField('BitsPerSample')

        typ = {32: np.uint32, 16: np.uint16, 8: np.uint8, 64: np.uint64}.get(bits)
        if typ is None:
            if bits==1: # TODO: check for correctness
                typ = np.uint8
                itemsize = 1
            elif bits==4: # TODO: check for correctness
                typ = np.uint32
                itemsize = 4
            else:
                raise NotImplementedError (`bits`)
        else:
            itemsize = bits/8            
        size = width * height * itemsize
        arr = np.zeros((height, width), typ)

        pos = 0
        elem = None
        for strip in range (self.NumberOfStrips()):
            if elem is None:
                elem = self.ReadRawStrip(strip, arr.ctypes.data + pos, size)
            elif elem:
                elem = self.ReadRawStrip(strip, arr.ctypes.data + pos, min(size - pos, elem))
            pos += elem
        return arr

    def write_image(self, arr):
        """ Write array as TIFF image.
        """
        shape=arr.shape
        if len(shape)!=2:
            raise NotImplementedError (`shape`)
        height, width = shape
        bits = arr.itemsize * 8
        size = width * height * arr.itemsize

        self.SetField(TIFFTAG_IMAGEWIDTH, width)
        self.SetField(TIFFTAG_IMAGELENGTH, height)
        self.SetField(TIFFTAG_BITSPERSAMPLE, bits)

        #self.SetField(TIFFTAG_SAMPLESPERPIXEL, 1)
        self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
        self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_RIGHTTOP)
        self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
        
        self.WriteRawStrip(0, arr.ctypes.data, size)
        self.WriteDirectory()

    def iter_images(self, verbose=False):
        """ Iterator of all images in a TIFF file.
        """
        yield self.read_image(verbose=verbose)
        if not self.LastDirectory():
            while 1:
                self.ReadDirectory()
                yield self.read_image(verbose=verbose)
                if self.LastDirectory():
                    break

    def __del__(self):
        self.close()

    def FileName(self): return libtiff.TIFFFileName(self)
    def CurrentRow(self): return libtiff.TIFFCurrentRow(self)
    def CurrentStrip(self): return libtiff.TIFFCurrentStrip(self)
    def CurrentTile(self): return libtiff.TIFFCurrentTile(self)
    def CurrentDirectory(self): return libtiff.TIFFCurrentDirectory(self)
    def LastDirectory(self): return libtiff.TIFFLastDirectory(self)
    def ReadDirectory(self): return libtiff.TIFFReadDirectory(self)
    def WriteDirectory(self): 
        r = libtiff.TIFFWriteDirectory(self)
        assert r==1, `r`
    def Fileno(self): return libtiff.TIFFFileno(self)
    def GetMode(self): return libtiff.TIFFGetMode(self)
    def IsTiled(self): return libtiff.TIFFIsTiled(self)
    def IsByteSwapped(self): return libtiff.TIFFIsByteSwapped(self)
    def IsUpSampled(self): return libtiff.TIFFIsUpSampled(self)
    def IsMSB2LSB(self): return libtiff.TIFFIsMSB2LSB(self)
    def NumberOfStrips(self): return libtiff.TIFFNumberOfStrips(self).value

    def ReadRawStrip(self, strip, buf, size): 
        return libtiff.TIFFReadRawStrip(self, strip, buf, size).value

    def WriteRawStrip(self, strip, buf, size): 
        r = libtiff.TIFFWriteRawStrip(self, strip, buf, size)
        assert r.value==size,`r.value, size`

    closed = False
    def close(self): 
        if not self.closed and self.value is not None:
            libtiff.TIFFClose(self)
            self.closed = True
        return
    #def (self): return libtiff.TIFF(self)

    def GetField(self, tag):
        """ Return TIFF field value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """

        if isinstance(tag, str):
            tag = eval('TIFFTAG_' + tag.upper())
        t = tifftags.get(tag)
        if t is None:
            print 'Warning: no tag %r defined' % (tag)
            return
        data_type, convert = t
        data = data_type()
        r = libtiff.TIFFGetField(self, tag, ctypes.byref(data))
        if not r: # tag not defined for current directory
            return None
        return convert(data)

    def SetField (self, tag, value):
        """ Set TIFF field value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """

        if isinstance(tag, str):
            tag = eval('TIFFTAG_' + tag.upper())
        t = tifftags.get(tag)
        if t is None:
            print 'Warning: no tag %r defined' % (tag)
            return
        data_type, convert = t
        data = data_type(value)
        libtiff.TIFFSetField.argtypes = libtiff.TIFFSetField.argtypes[:-1] + [data_type]
        r = libtiff.TIFFSetField(self, tag, data)
        assert r, `r`

    def info(self):
        """ Return a string containing <tag name: field value> map.
        """
        l = []
        l.append ('FileName: %s' % (self.FileName()))
        for tagname in ['Artist', 'CopyRight', 'DateTime', 'DocumentName',
                        'HostComputer', 'ImageDescription', 'InkNames',
                        'Make', 'Model', 'PageName', 'Software', 'TargetPrinter',
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
                        #'Stonits',
                        'XPosition', 'YPosition', 'XResolution', 'YResolution',
                        'PrimaryChromaticities', 'ReferenceBlackWhite',
                        'WhitePoint', 'YCBCRCoefficients'
                        ]:
            v = self.GetField(tagname)
            if v:
                if isinstance (v, int):
                    v = define_to_name_map.get(tagname, {}).get(v, v)
                l.append('%s: %s' % (tagname, v))
        return '\n'.join(l)
        

libtiff.TIFFGetVersion.restype = ctypes.c_char_p
libtiff.TIFFGetVersion.argtypes = []

libtiff.TIFFOpen.restype = TIFF
libtiff.TIFFOpen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

libtiff.TIFFFileName.restype = ctypes.c_char_p
libtiff.TIFFFileName.argtypes = [TIFF]

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
libtiff.TIFFSetField.argtypes = [TIFF, c_ttag_t, ctypes.c_void_p] # last item is reset in TIFF.SetField method

libtiff.TIFFNumberOfStrips.restype = c_tstrip_t
libtiff.TIFFNumberOfStrips.argtypes = [TIFF]

libtiff.TIFFReadRawStrip.restype = c_tsize_t
libtiff.TIFFReadRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFWriteRawStrip.restype = c_tsize_t
libtiff.TIFFWriteRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFClose.restype = None
libtiff.TIFFClose.argtypes = [TIFF]


def _test_read(filename=None):
    import sys
    if filename is None:
        if len(sys.argv) != 2:
            print 'Run `libtiff.py <filename>` for testing.'
            return
        filename = sys.argv[1]
    print 'Trying to open', filename, '...',
    tiff = TIFF.open(filename)
    print 'ok'
    print 'Trying to show info ...\n','-'*10
    print tiff.info()
    print '-'*10,'ok'
    print 'Trying show images ...'
    for image in tiff.iter_images(verbose=True):
        print image
    print '\tok'

def _test_write():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros ((5,6), np.uint32)
    for i in range(arr.shape[0]):
        for j in range (arr.shape[1]):
            arr[i,j] = i + 10*j
    print arr
    tiff.write_image(arr)
    del tiff

if __name__=='__main__':
    _test_write()
    _test_read()


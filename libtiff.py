#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

Homepage:  http://pylibtiff.googlecode.com/
"""
__author__ = 'Pearu Peterson'
__date__ = 'April 2009'
__license__ = 'BSD'
__version__ = '0.2-svn'
__all__ = ['libtiff', 'TIFF']

import os
import sys
import numpy as np
from numpy import ctypeslib
import ctypes
import ctypes.util

if os.name=='nt':
    # assume that the directory of libtiff3.dll is in PATH.
    lib = ctypes.util.find_library('libtiff3')
    if lib is None:
        # try default installation path:
        lib = r'C:\Program Files\GnuWin32\bin\libtiff3.dll'
        if os.path.isfile (lib):
            print 'You should add %r to PATH environment variable and reboot.' % (os.path.dirname (lib))
        else:
            lib = None
else:
    lib = ctypes.util.find_library('tiff')
if lib is None:
    raise ImportError('Failed to find TIFF library. Make sure that libtiff is installed and its location is listed in PATH|LD_LIBRARY_PATH|..')

libtiff = ctypes.cdll.LoadLibrary(lib)

libtiff.TIFFGetVersion.restype = ctypes.c_char_p
libtiff.TIFFGetVersion.argtypes = []

libtiff_version_str = libtiff.TIFFGetVersion()
i = libtiff_version_str.lower().split().index('version')
assert i!=-1,`libtiff_version_str`
libtiff_version = libtiff_version_str.split()[i+1]

tiff_h_name = 'tiff_h_%s' % (libtiff_version.replace ('.','_'))

try:
    exec 'import %s as tiff_h' % (tiff_h_name)
except ImportError:
    tiff_h = None

if tiff_h is None:
    include_tiff_h = os.path.join('/usr','include','tiff.h')
    assert os.path.isfile(include_tiff_h), `include_tiff_h, lib`
    # Read TIFFTAG_* constants for the header file:
    f = open (include_tiff_h, 'r')
    l = []
    d = {}
    for line in f.readlines():
        if not line.startswith('#define'): continue
        words = line[7:].lstrip().split()[:2]
        if len (words)!=2: continue
        name, value = words
        i = value.find('/*')
        if i!=-1: value = value[:i]
        if value in d:
            value = d[value]
        else:
            value = eval(value)
        d[name] = value
        l.append('%s = %s' % (name, value))
    f.close()


    fn = os.path.join (os.path.dirname (os.path.abspath (__file__)), tiff_h_name+'.py')
    print 'Generating %r' % (fn)
    f = open(fn, 'w')
    f.write ('\n'.join(l) + '\n')
    f.close()
else:
    d = tiff_h.__dict__

define_to_name_map = dict(Orientation={}, Compression={},
                          PhotoMetric={}, PlanarConfig={},
                          SampleFormat={}, FillOrder={},
                          FaxMode={}, TiffTag = {}
                          )

name_to_define_map = dict(Orientation={}, Compression={},
                          PhotoMetric={}, PlanarConfig={},
                          SampleFormat={}, FillOrder={},
                          FaxMode={}, TiffTag = {}
                          )

for name, value in d.items():
    if name.startswith ('_'): continue
    exec '%s = %s' % (name, value)
    for n in define_to_name_map:
        if name.startswith(n.upper()):
            define_to_name_map[n][value] = name        
            name_to_define_map[n][name] = value

                
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

def debug(func):
    return func
    def new_func(*args, **kws):
        print 'Calling',func.__name__
        r = func (*args, **kws)
        return r
    return new_func

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

    @staticmethod
    def get_tag_name(tagvalue):
        for kind in define_to_name_map:
            tagname = define_to_name_map[kind].get (tagvalue)
            if tagname is not None:
                return tagname

    @staticmethod
    def get_tag_define(tagname):
        if '_' in tagname:
            kind, name = tagname.rsplit('_',1)
            return name_to_define_map[kind.title()][tagname.upper()]
        for kind in define_to_name_map:
            tagvalue = name_to_define_map[kind].get((kind+'_'+tagname).upper ())
            if tagvalue is not None:
                return tagvalue

    @classmethod
    def open(cls, filename, mode='r'):
        """ Open tiff file as TIFF.
        """
        tiff = libtiff.TIFFOpen(filename, mode)
        if tiff.value is None:
            raise TypeError ('Failed to open file '+`filename`)
        return tiff

    @staticmethod
    def get_numpy_type(bits, sample_format=None):
        """ Return numpy dtype corresponding to bits and sample format.
        """
        typ = None
        if sample_format==SAMPLEFORMAT_IEEEFP:
            typ = getattr(np,'float%s' % (bits))
        elif sample_format==SAMPLEFORMAT_UINT or sample_format is None:
            typ = getattr(np,'uint%s' % (bits))
        elif sample_format==SAMPLEFORMAT_INT:
            typ = getattr(np,'int%s' % (bits))
        elif sample_format==SAMPLEFORMAT_COMPLEXIEEEFP:
            typ = getattr(np,'complex%s' % (bits))
        else:
            raise NotImplementedError (`sample_format`)
        return typ

    @debug
    def read_image(self, verbose=False):
        """ Read image from TIFF and return it as an array.
        """
        width = self.GetField('ImageWidth')
        height = self.GetField('ImageLength')
        bits = self.GetField('BitsPerSample')
        sample_format = self.GetField('SampleFormat')
        compression = self.GetField('Compression')

        typ = self.get_numpy_type(bits, sample_format)

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

        if compression==COMPRESSION_NONE:
            ReadStrip = self.ReadRawStrip
        else:
            ReadStrip = self.ReadEncodedStrip

        pos = 0
        elem = None
        for strip in range (self.NumberOfStrips()):
            if elem is None:
                elem = ReadStrip(strip, arr.ctypes.data + pos, size)
            elif elem:
                elem = ReadStrip(strip, arr.ctypes.data + pos, min(size - pos, elem))
            pos += elem
        return arr

    @staticmethod
    def _fix_compression(value):
        if isinstance(value, int):
            return value
        elif value is None:
            return COMPRESSION_NONE
        elif isinstance(value, str):
            return name_to_define_map['Compression']['COMPRESSION_'+value.upper()]
        else:
            raise NotImplementedError(`value`)

    @staticmethod
    def _fix_sampleformat(value):
        if isinstance(value, int):
            return value
        elif value is None:
            return SAMPLEFORMAT_UINT            
        elif isinstance(value, str):
            return dict(int=SAMPLEFORMAT_INT, uint=SAMPLEFORMAT_UINT,
                        float=SAMPLEFORMAT_IEEEFP, complex=SAMPLEFORMAT_COMPLEXIEEEFP)[value.lower()]
        else:
            raise NotImplementedError(`value`)

    def write_image(self, arr, compression=None):
        """ Write array as TIFF image.

        Parameters
        ----------
        arr : :numpy:`ndarray`
          Specify image data of rank 1 to 3.
        compression : {None, 'ccittrle', 'ccittfax3','ccitt_t4','ccittfax4','ccitt_t6','lzw','ojpeg','jpeg','next','ccittrlew','packbits','thunderscan','it8ctpad','it8lw','it8mp','it8bl','pixarfilm','pixarlog','deflate','adobe_deflate','dcs','jbig','sgilog','sgilog24','jp2000'}
        """
        COMPRESSION = self._fix_compression (compression)

        arr = np.ascontiguousarray(arr)
        sample_format = None
        if arr.dtype in np.sctypes['float']:
            sample_format = SAMPLEFORMAT_IEEEFP
        elif arr.dtype in np.sctypes['uint']:
            sample_format = SAMPLEFORMAT_UINT
        elif arr.dtype in np.sctypes['int']:
            sample_format = SAMPLEFORMAT_INT
        elif arr.dtype in np.sctypes['complex']:
            sample_format = SAMPLEFORMAT_COMPLEXIEEEFP
        else:
            raise NotImplementedError(`arr.dtype`)
        shape=arr.shape
        bits = arr.itemsize * 8

        if compression==COMPRESSION_NONE:
            WriteStrip = self.WriteRawStrip
        else:
            WriteStrip = self.WriteEncodedStrip

        if len(shape)==1:
            width, = shape
            size = width * arr.itemsize
            self.SetField(TIFFTAG_IMAGEWIDTH, width)
            self.SetField(TIFFTAG_IMAGELENGTH, 1)
            self.SetField(TIFFTAG_BITSPERSAMPLE, bits)
            self.SetField(TIFFTAG_COMPRESSION, COMPRESSION)
            self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
            self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_RIGHTTOP)
            self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
            if sample_format is not None:
                self.SetField(TIFFTAG_SAMPLEFORMAT, sample_format)
            WriteStrip(0, arr.ctypes.data, size)
            self.WriteDirectory()

        elif len(shape)==2:
            height, width = shape
            size = width * height * arr.itemsize

            self.SetField(TIFFTAG_IMAGEWIDTH, width)
            self.SetField(TIFFTAG_IMAGELENGTH, height)
            self.SetField(TIFFTAG_BITSPERSAMPLE, bits)
            self.SetField(TIFFTAG_COMPRESSION, COMPRESSION)
            #self.SetField(TIFFTAG_SAMPLESPERPIXEL, 1)
            self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
            self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_RIGHTTOP)
            self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)

            if sample_format is not None:
                self.SetField(TIFFTAG_SAMPLEFORMAT, sample_format)

            WriteStrip(0, arr.ctypes.data, size)            
            self.WriteDirectory()
        elif len(shape)==3:
            depth, height, width = shape
            size = width * height * arr.itemsize
            for n in range(depth):
                self.SetField(TIFFTAG_IMAGEWIDTH, width)
                self.SetField(TIFFTAG_IMAGELENGTH, height)
                self.SetField(TIFFTAG_BITSPERSAMPLE, bits)
                self.SetField(TIFFTAG_COMPRESSION, COMPRESSION)
                #self.SetField(TIFFTAG_SAMPLESPERPIXEL, 1)
                self.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
                self.SetField(TIFFTAG_ORIENTATION, ORIENTATION_RIGHTTOP)
                self.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)

                if sample_format is not None:
                    self.SetField(TIFFTAG_SAMPLEFORMAT, sample_format)

                WriteStrip(0, arr[n].ctypes.data, size)
                self.WriteDirectory()
        else:
            raise NotImplementedError (`shape`)

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

    @debug
    def FileName(self): return libtiff.TIFFFileName(self)
    @debug
    def CurrentRow(self): return libtiff.TIFFCurrentRow(self)
    @debug
    def CurrentStrip(self): return libtiff.TIFFCurrentStrip(self)
    @debug
    def CurrentTile(self): return libtiff.TIFFCurrentTile(self)
    @debug
    def CurrentDirectory(self): return libtiff.TIFFCurrentDirectory(self)
    @debug
    def LastDirectory(self): return libtiff.TIFFLastDirectory(self)
    @debug
    def ReadDirectory(self): return libtiff.TIFFReadDirectory(self)
    @debug
    def WriteDirectory(self): 
        r = libtiff.TIFFWriteDirectory(self)
        assert r==1, `r`
    @debug
    def SetDirectory(self, dirnum): return libtiff.TIFFSetDirectory(self, dirnum)
    @debug
    def Fileno(self): return libtiff.TIFFFileno(self)
    @debug
    def GetMode(self): return libtiff.TIFFGetMode(self)
    @debug
    def IsTiled(self): return libtiff.TIFFIsTiled(self)
    @debug
    def IsByteSwapped(self): return libtiff.TIFFIsByteSwapped(self)
    @debug
    def IsUpSampled(self): return libtiff.TIFFIsUpSampled(self)
    @debug
    def IsMSB2LSB(self): return libtiff.TIFFIsMSB2LSB(self)
    @debug
    def NumberOfStrips(self): return libtiff.TIFFNumberOfStrips(self).value

    #@debug
    def ReadRawStrip(self, strip, buf, size): 
        return libtiff.TIFFReadRawStrip(self, strip, buf, size).value
    def ReadEncodedStrip(self, strip, buf, size): 
        return libtiff.TIFFReadEncodedStrip(self, strip, buf, size).value

    def StripSize(self): 
        return libtiff.TIFFStripSize(self).value
    def RawStripSize(self, strip): 
        return libtiff.TIFFStripSize(self, strip).value

    @debug
    def WriteRawStrip(self, strip, buf, size): 
        r = libtiff.TIFFWriteRawStrip(self, strip, buf, size)
        assert r.value==size,`r.value, size`

    @debug
    def WriteEncodedStrip(self, strip, buf, size): 
        r = libtiff.TIFFWriteEncodedStrip(self, strip, buf, size)
        assert r.value==size,`r.value, size`

    closed = False
    def close(self, libtiff=libtiff): 
        if not self.closed and self.value is not None:
            libtiff.TIFFClose(self)
            self.closed = True
        return
    #def (self): return libtiff.TIFF(self)

    @debug
    def GetField(self, tag, ignore_undefined_tag=True):
        """ Return TIFF field value with tag.

        tag can be numeric constant TIFFTAG_<tagname> or a
        string containing <tagname>.
        """
        if tag in ['PixelSizeX', 'PixelSizeY', 'RelativeTime']:
            descr = self.GetField('ImageDescription')
            if not descr:
                return
            i = descr.find (tag)
            if i==-1:
                return
            value = eval(descr[i+len (tag):].lstrip().split()[0])
            return value
        if isinstance(tag, str):
            tag = eval('TIFFTAG_' + tag.upper())
        t = tifftags.get(tag)
        if t is None:
            if not ignore_undefined_tag:
                print 'Warning: no tag %r defined' % (tag)
            return
        data_type, convert = t
        data = data_type()
        r = libtiff.TIFFGetField(self, tag, ctypes.byref(data))
        if not r: # tag not defined for current directory
            return None
        return convert(data)

    #@debug
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
        return r

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
                        'WhitePoint', 'YCBCRCoefficients',
                        'PixelSizeX','PixelSizeY', 'RelativeTime'
                        ]:
            v = self.GetField(tagname)
            if v:
                if isinstance (v, int):
                    v = define_to_name_map.get(tagname, {}).get(v, v)
                l.append('%s: %s' % (tagname, v))
        return '\n'.join(l)
        
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
        for name, value in kws.items():
            define = TIFF.get_tag_define(name)
            assert define is not None
            if name=='compression':
                value = TIFF._fix_compression(value)
            if name=='sampleformat':
                value = TIFF._fix_sampleformat(value)
            define_rewrite[define] = value
        name_define_list = name_to_define_map['TiffTag'].items()
        self.SetDirectory(0)
        self.ReadDirectory()
        while 1:
            other.SetDirectory(self.CurrentDirectory())
            bits = self.GetField('BitsPerSample')
            sample_format = self.GetField('SampleFormat')
            assert bits >=8, `bits, sample_format, dtype`
            itemsize = bits // 8
            dtype = self.get_numpy_type(bits, sample_format)
            for name, define in name_define_list:
                orig_value = self.GetField(define)
                if orig_value is None and define not in define_rewrite:
                    continue
                if name.endswith('OFFSETS') or name.endswith('BYTECOUNTS'):
                    continue
                if define in define_rewrite:
                    value = define_rewrite[define]
                else:
                    value = orig_value
                if value is None:
                    continue
                other.SetField(define, value)
            new_bits = other.GetField('BitsPerSample')
            new_sample_format = other.GetField('SampleFormat')
            new_dtype = other.get_numpy_type(new_bits, new_sample_format)
            assert new_bits >=8, `new_bits, new_sample_format, new_dtype`
            new_itemsize = new_bits // 8
            strip_size = self.StripSize()
            new_strip_size = self.StripSize()
            buf = np.zeros(strip_size // itemsize, dtype)
            for strip in range(self.NumberOfStrips()):
                elem = self.ReadEncodedStrip(strip, buf.ctypes.data, strip_size)
                if elem>0:
                    new_buf = buf.astype(new_dtype)
                    other.WriteEncodedStrip(strip, new_buf.ctypes.data, elem * new_itemsize)
            self.ReadDirectory()
            if self.LastDirectory ():
                break
        other.close ()

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
libtiff.TIFFSetField.argtypes = [TIFF, c_ttag_t, ctypes.c_void_p] # last item is reset in TIFF.SetField method

libtiff.TIFFNumberOfStrips.restype = c_tstrip_t
libtiff.TIFFNumberOfStrips.argtypes = [TIFF]

libtiff.TIFFReadRawStrip.restype = c_tsize_t
libtiff.TIFFReadRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFWriteRawStrip.restype = c_tsize_t
libtiff.TIFFWriteRawStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFReadEncodedStrip.restype = c_tsize_t
libtiff.TIFFReadEncodedStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFWriteEncodedStrip.restype = c_tsize_t
libtiff.TIFFWriteEncodedStrip.argtypes = [TIFF, c_tstrip_t, c_tdata_t, c_tsize_t]

libtiff.TIFFStripSize.restype = c_tsize_t
libtiff.TIFFStripSize.argtypes = [TIFF]

libtiff.TIFFRawStripSize.restype = c_tsize_t
libtiff.TIFFRawStripSize.argtypes = [TIFF, c_tstrip_t]

libtiff.TIFFClose.restype = None
libtiff.TIFFClose.argtypes = [TIFF]

# Support for TIFF warning and error handlers:
TIFFWarningHandler = ctypes.CFUNCTYPE(None,
                                      ctypes.c_char_p, # Module
                                      ctypes.c_char_p, # Format
                                      ctypes.c_void_p) # va_list
TIFFErrorHandler = ctypes.CFUNCTYPE(None,
                                      ctypes.c_char_p, # Module
                                      ctypes.c_char_p, # Format
                                      ctypes.c_void_p) # va_list

# This has to be at module scope so it is not garbage-collected
_null_warning_handler = TIFFWarningHandler(lambda module, fmt, va_list: None)
_null_error_handler = TIFFErrorHandler(lambda module, fmt, va_list: None)

def suppress_warnings():
    libtiff.TIFFSetWarningHandler(_null_warning_handler)
def suppress_errors():
    libtiff.TIFFSetErrorHandler(_null_error_handler)

def _test_read(filename=None):
    import sys
    import time
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
    t = time.time ()
    i = 0
    for image in tiff.iter_images(verbose=True):
        #print image.min(), image.max(), image.mean ()
        i += 1
    print '\tok',(time.time ()-t)*1e3,'ms',i,'images'

def _test_write():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros ((5,6), np.uint32)
    for i in range(arr.shape[0]):
        for j in range (arr.shape[1]):
            arr[i,j] = i + 10*j
    print arr
    tiff.write_image(arr)
    del tiff

def _test_write_float():
    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='w')
    arr = np.zeros ((5,6), np.float64)
    for i in range(arr.shape[0]):
        for j in range (arr.shape[1]):
            arr[i,j] = i + 10*j
    print arr
    tiff.write_image(arr)
    del tiff

    tiff = TIFF.open('/tmp/libtiff_test_write.tiff', mode='r')
    print tiff.info()
    arr2 = tiff.read_image()
    print arr2

def _test_copy():
    tiff = TIFF.open('/tmp/libtiff_test_compression.tiff', mode='w')
    arr = np.zeros ((5,6), np.uint32)
    for i in range(arr.shape[0]):
        for j in range (arr.shape[1]):
            arr[i,j] = 1+i + 10*j
    #from scipy.stats import poisson
    #arr = poisson.rvs (arr)
    tiff.SetField('ImageDescription', 'Hey\nyou')
    tiff.write_image(arr, compression='lzw')
    del tiff

    tiff = TIFF.open('/tmp/libtiff_test_compression.tiff', mode='r')
    print tiff.info()
    arr2 = tiff.read_image()

    assert (arr==arr2).all(),'arrays not equal'

    for compression in ['none','lzw','deflate']:
        for sampleformat in ['int','uint','float']:
            for bitspersample in [256,128,64,32,16,8]:
                if sampleformat=='float' and (bitspersample < 32 or bitspersample > 128):
                    continue
                if sampleformat in ['int','uint'] and bitspersample > 64:
                    continue
                #print compression, sampleformat, bitspersample
                tiff.copy ('/tmp/libtiff_test_copy2.tiff', 
                           compression=compression,
                           imagedescription='hoo',
                           sampleformat=sampleformat,
                           bitspersample=bitspersample)
                tiff2 = TIFF.open('/tmp/libtiff_test_copy2.tiff', mode='r')
                arr3 = tiff2.read_image()
                assert (arr==arr3).all(),'arrays not equal %r' % ((compression, sampleformat, bitspersample),)
    print 'test copy ok'

if __name__=='__main__':
    #_test_write_float()
    #_test_write()
    #_test_read()
    _test_copy()


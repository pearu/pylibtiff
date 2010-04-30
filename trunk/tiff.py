"""
tiff - implements numpy.memmap based TIFF reader
"""

__all__ = ['TIFFfile']

import os
import sys
import numpy

#<TagName> <Hex> <Type> <Number of values>
tag_info = '''
# standard tags:
NewSubfileType FE LONG 1
SubfileType FF SHORT 1
ImageWidth 100 SHORT|LONG 1
ImageLength 101 SHORT|LONG 1
BitsPerSample 102 SHORT SamplesPerPixel
Compression 103 SHORT 1
  Uncompressed 1
  CCITT1D 2
  Group3Fax 3
  Group4Fax 4
  LZW 5
  JPEG 6
  PackBits 32773
PhotometricInterpretation 106 SHORT 1
  WhiteIsZero 0
  BlackIsZero 1
  RGB 2
  RGBPalette 3
  TransparencyMask 4
  CMYK 5
  YCbCr 6
  CIELab 8
Threshholding 107 SHORT 1
CellWidth 108 SHORT 1
CellLength 109 SHORT 1
FillOrder 10A SHORT 1
DocumentName 10D ASCII
ImageDescription 10E ASCII
Make 10F ASCII
Model 110 ASCII
StripOffsets 111 SHORT|LONG StripsPerImage
Orientation 112 SHORT 1
SamplesPerPixel 115 SHORT 1
RowsPerStrip 116 SHORT|LONG 1
StripByteCounts 117 LONG|SHORT StripsPerImage
MinSampleValue 118 SHORT SamplesPerPixel
MaxSampleValue 119 SHORT SamplesPerPixel
XResolution 11A RATIONAL 1
YResolution 11B RATIONAL 1
PlanarConfiguration 11C SHORT 1
PageName 11D ASCII
XPosition 11E RATIONAL
YPosition 11F RATIONAL
FreeOffsets 120 LONG
FreeByteCounts 121 LONG
GrayResponseUnit 122 SHORT 1
GrayResponseCurve 123 SHORT 2**BitsPerSample
T4Options 124 LONG 1
T6Options 125 LONG 1
ResolutionUnit 128 SHORT 1
PageNumber 129 SHORT 2
TransferFunction 12D SHORT (1|SamplesPerPixel)*2**BitsPerSample
Software 131 ASCII
DateTime 132 ASCII 20
Artist 13B ASCII
HostComputer 13C ASCII
Predictor 13D SHORT 1
WhitePoint 13E RATIONAL 2
PrimaryChromaticities 13F RATIONAL 6
ColorMap 140 SHORT 3*(2**BitsPerSample)
HalftoneHints 141 SHORT 2
TileWidth 142 SHORT|LONG 1
TileLength 143 SHORT|LONG 1
TileOffsets 144 LONG TilesPerImage
TileByteCounts 145 SHORT|LONG TilesPerImage
InkSet 14C SHORT 1
InkNames 14D ASCII <total number of chars in all ink name strings, including zeros>
NumberOfInks 14E SHORT 1
DotRange 150 BYTE|SHORT 2|2*NumberOfInks
TargetPrinter 151 ASCII any
ExtraSamples 152 BYTE <number of extra components per pixel>
SampleFormat 153 SHORT SamplesPerPixel
SMinSampleValue 154 Any SamplesPerPixel
SMaxSampleValue 155 Any SamplesPerPixel
TransferRange 156 SHORT 6
JPEGProc 200 SHORT 1
JPEGInterchangeFormat 201 LONG 1
JPEGInterchangeFormatLength 202 LONG 1
JPEGRestartInterval 203 SHORT 1
JPEGLosslessPredictos 205 SHORT SamplesPerPixel
JPEGPointTransforms 206 SHORT SamplesPerPixel
JPEGQTables 207 LONG SamplesPerPixel
JPEGDCTables 208 LONG SamplesPerPixel
JPEGACTables 209 LONG SamplesPerPixel
YCbCrCoefficients 211 RATIONAL 3
YCbCrSubSampling 212 SHORT 2
YCbCrPositioning 213 SHORT 1
ReferenceBlackWhite 214 LONG 2*SamplesPerPixel
Copyright 8298 ASCII Any

# non-standard tags:
CZ_LSMInfo 866C CZ_LSM
'''

rational = numpy.dtype([('numer', numpy.uint32), ('denom', numpy.uint32)])
srational = numpy.dtype([('numer', numpy.int32), ('denom', numpy.int32)])

type2name = {1:'BYTE', 2:'ASCII', 3:'SHORT', 4:'LONG', 5:'RATIONAL', # two longs, lsm uses it for float64
             6:'SBYTE', 7:'UNDEFINED', 8:'SSHORT', 9:'SLONG', 10:'SRATIONAL',
             11:'FLOAT', 12:'DOUBLE',
             }
name2type = dict((v,k) for k,v in type2name.items())
type2bytes = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
type2dtype = {1:numpy.uint8, 2:numpy.uint8, 3:numpy.uint16, 4:numpy.uint32, 5:rational,
              6:numpy.int8, 8:numpy.int16, 9:numpy.int32,10:srational,
              11:numpy.float32, 12:numpy.float64}

tag_value2name = {}
tag_name2value = {}
tag_value2type = {}
for line in tag_info.split('\n'):
    if not line or line.startswith('#'): continue
    if line[0]==' ':
        pass
    else:
        n,h,t = line.split()[:3]
        h = eval('0x'+h)
        tag_value2name[h]=n
        tag_value2type[h]=t
        tag_name2value[n]=h

IFDEntry_init_hooks = []

# Register CZ LSM support:
import lsm
lsm.register(locals())

class TIFFfile:
    """ Holds a numpy.memmap of a TIFF file.
    """

    def __init__(self, filename, mode='r'):
        if mode!='r':
            raise NotImplementedError(`mode`)
        self.filename = filename
        self.data = numpy.memmap(filename, dtype=numpy.ubyte, mode=mode)
        self.init()

    def init(self):
        byteorder = self.get_uint16(0)
        if byteorder==0x4949:
            self.endian = 'little'
        elif byteorder==0x4d4d:
            self.endian = 'big'
        else:
            raise ValueError('unrecognized byteorder: %s' % (hex(byteorder)))
        magic = self.get_uint16(2)
        if magic!=42:
            raise ValueError('wrong magic number for TIFF file: %s' % (magic))
        self.IFD0 = IFD0 = self.get_uint32(4)
        n = self.get_uint16(IFD0)
        IFD_list = []
        IFD_offset = IFD0
        while IFD_offset:
            n = self.get_uint16(IFD_offset)
            ifd = IFD()
            for i in range(n):
                entry = IFDEntry(self, IFD_offset + 2 + i*12)
                ifd.append(entry)
            IFD_list.append(ifd)
            IFD_offset = self.get_uint32(IFD_offset + 2 + n*12)
        self.IFD = IFD_list

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.filename)

    def get_uint16(self, offset):
        return self.data[offset:offset+2].view(dtype=numpy.uint16)[0]
    def get_uint32(self, offset):
        return self.data[offset:offset+4].view(dtype=numpy.uint32)[0]
    def get_int16(self, offset):
        return self.data[offset:offset+2].view(dtype=numpy.int16)[0]
    def get_int32(self, offset):
        return self.data[offset:offset+4].view(dtype=numpy.int32)[0]
    def get_float32(self, offset):
        return self.data[offset:offset+4].view(dtype=numpy.float32)[0]
    def get_float64(self, offset):
        return self.data[offset:offset+8].view(dtype=numpy.float64)[0]
    get_short = get_uint16
    get_long = get_uint32
    get_double = get_float64

    def get_value(self, offset, type):
        values = self.get_values(offset, type, 1)
        if values is not None:
            return values[0]
    def get_values(self, offset, typ, count):
        if isinstance(typ, numpy.dtype):
            dtype = typ
            bytes = typ.itemsize
        elif isinstance(typ, type) and  issubclass(typ, numpy.generic):
            dtype = typ
            bytes = typ().itemsize
        else:
            if isinstance(typ, str):
                typ = name2type.get(typ)
            dtype = type2dtype.get(typ)
            bytes = type2bytes.get(typ)
            if dtype is None or bytes is None:
                sys.stderr.write('get_values: incomplete info for type=%r: dtype=%s, bytes=%s' % (typ, dtype, bytes))
                return
        return self.data[offset:offset+bytes*count].view(dtype=dtype)

    def get_string(self, offset, length = None):
        if length is None:
            i = 0
            while self.data[offset+i]:
                i += 1
            length = i
        string = self.get_values(offset, 'BYTE', length).tostring()
        return string

class IFD:
    """ Image File Directory data structure.
    """
    def __init__(self):
        self.entries = []
    def append(self, entry):
        self.entries.append (entry)

    def __str__(self):
        l = []
        for entry in self.entries:
            l.append(str (entry))
        return '\n'.join(l)
        

class IFDEntry:
    """ Entry for Image File Directory data structure.
    """
    def __init__(self, tiff, offset):
        self.tiff = tiff
        self.offset = offset

        # initialization:
        self.tag = tiff.get_uint16(offset)
        self.type = tiff.get_uint16(offset+2)
        self.count = tiff.get_uint32(offset+4)
        for hook in IFDEntry_init_hooks:
            hook(self)
        
        bytes = type2bytes.get(self.type,0)
        if self.count==1 and 1<=bytes<=4:
            value = tiff.get_value(offset+8, self.type)
        else:
            self.offset = tiff.get_int32(offset+8)
            value = tiff.get_values(self.offset, self.type, self.count)
        if value is not None:
            self.value = value
        self.tag_name = tag_value2name.get(self.tag,'TAG%s' % (hex(self.tag),))
        self.type_name = type2name.get(self.type, 'TYPE%s' % (self.type,))
        
    def __str__(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance (r, str):
                return r
        if hasattr(self, 'value'):
            return 'IFDEntry(tag=%(tag_name)s, value=%(value)r)' % (self.__dict__)
        else:
            return 'IFDEntry(tag=%(tag_name)s, type=%(type_name)s, count=%(count)s, offset=%(offset)s)' % (self.__dict__)

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.tiff, self.offset)

def main ():
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        raise ValueError('File %r does not exists' % (filename))

    t = TIFFfile(filename)
    e = t.IFD[0].entries[-1]
    assert e.is_lsm
    print e
    #print lsm.timestamps(e)
    print lsm.channelwavelength(e)

if __name__ == '__main__':
    main()


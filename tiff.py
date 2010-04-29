
import os
import sys
import numpy

import lsm

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

lsmdtype = numpy.dtype([
    ('MagicNumber',numpy.uint32),
    ('StructureSize',numpy.int32),
    ('DimensionX',numpy.int32), ('DimensionY',numpy.int32), ('DimensionZ',numpy.int32),
    ('DimensionChannels', numpy.int32),('DimensionTime', numpy.int32),
    ('SDataType', numpy.int32), # 1: uint8, 2: uint12, 5: float32, 0: see OffsetChannelDataTypes
    ('ThumbnailX', numpy.int32), ('ThumbnailY', numpy.int32),
    ('VoxelSizeX', numpy.float64), ('VoxelSizeY', numpy.float64), ('VoxelSizeZ', numpy.float64),
    ('OriginX', numpy.float64), ('OriginY', numpy.float64), ('OriginZ', numpy.float64),
    ('ScanType', numpy.uint16),
    # 0:xyz-scan, 1:z-scan, 2:line-scan 3:time xy,
    # 4: time xz (ver>=2.0), 5: time mean roi (ver>=2.0),
    # 6: time xyz (ver>=2.3), 7: spline scan (ver>=2.5),
    # 8: spline plane xz (ver>=2.5)
    # 9: time spline plane xz (ver>=2.5)
    # 10: point mode (ver>=3.0)
    ('SpectralScan', numpy.uint16), # 0:off, 1:on (ver>=3.0)
    ('DataType',numpy.uint32), # 0: original, 1: calculated, 2: animation
    ('OffsetVectorOverlay', numpy.uint32),
    ('OffsetInputLut',numpy.uint32), ('OffsetOutputLut',numpy.uint32),('OffsetChannelColors',numpy.uint32),
    ('TimeInterval',numpy.float64),
    ('OffsetChannelDataTypes',numpy.uint32),
    ('OffsetScanInformation',numpy.uint32),('OffsetKsData',numpy.uint32),('OffsetTimeStamps',numpy.uint32),
    ('OffsetEventList',numpy.uint32), ('OffsetRoi',numpy.uint32), ('OffsetBleachRoi',numpy.uint32),
    ('OffsetNextRecording',numpy.uint32),
    ('DisplayAspectX',numpy.float64), ('DisplayAspectY',numpy.float64), ('DisplayAspectZ',numpy.float64),
    ('DisplayAspectTime',numpy.float64),
    ('OffsetMeanOfRoisOverlay',numpy.uint32),
    ('OffsetTopoIsolineOverlay', numpy.uint32),
    ('OffsetTopoProfileOverlay', numpy.uint32),
    ('OffsetLinescanOverlay', numpy.uint32), ('ToolbarFlags', numpy.uint32),
    ('OffsetChannelWavelength', numpy.uint32),
    ('OffsetChannelFactors', numpy.uint32),
    ('ObjectiveSphereCorrection',numpy.float64),
    ('OffsetUnmixParameters',numpy.uint32),
    ('Reserved', numpy.dtype('(69,)u4')),
    ])


rational = numpy.dtype([('numer', numpy.uint32), ('denom', numpy.uint32)])
srational = numpy.dtype([('numer', numpy.int32), ('denom', numpy.int32)])

type2name = {1:'BYTE', 2:'ASCII', 3:'SHORT', 4:'LONG', 5:'RATIONAL', # two longs
             6:'SBYTE', 7:'UNDEFINED', 8:'SSHORT', 9:'SLONG', 10:'SRATIONAL',
             11:'FLOAT', 12:'DOUBLE',
             }
name2type = dict((v,k) for k,v in type2name.items())
type2bytes = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
type2dtype = {1:numpy.uint8, 2:numpy.string_, 3:numpy.uint16, 4:numpy.uint32, 5:rational,
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

lsmtag = tag_name2value['CZ_LSMInfo']
lsmtype = -lsmtag
type2name[lsmtype] = 'CZ_LSM'
type2dtype[lsmtype] = lsmdtype


class TIFFView:
    """ Data structure to access TIFF files via Numpy memmap.

    
    """

    def __init__(self, filename):
        self.data = numpy.memmap(filename, dtype=numpy.byte, mode='r')
        self.check()

    def check (self):
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
        self.IFD0 = self.get_uint32(4)

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
        if values is not None: return values[0]
    def get_values(self, offset, type, count):
        if isinstance(type, str):
            type = name2type.get(type)
        dtype = type2dtype.get(type)
        bytes = type2bytes.get(type)
        if dtype is None or bytes is None:
            return
        return self.data[offset:offset+bytes*count].view(dtype=dtype)

    def get_string(self, offset, length):
        string = self.get_values(offset, 'BYTE', length).tostring()
        return string
    
    def iter_IFD(self):
        IFD0 = self.IFD0
        n = self.get_uint16(IFD0)
        for i in range(n):
            yield IFDEntry(self, IFD0 + 2 + i*12)

class Entry:

    def __init__(self, entry, type_name, label, data):
        self.record = (entry, type_name, label, data)
        self.footer = None
        if type_name == 'ASCII':
            self.type = 2
            self.header = numpy.array([entry, 2, len(data)+1], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'LONG':
            self.type = 4
            self.header = numpy.array([entry, 4, 4], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'DOUBLE':
            self.type = 5
            self.header = numpy.array([entry, 5, 8], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'SUBBLOCK':
            self.type = 0
            self.header = numpy.array([entry, 0, 0], dtype=numpy.uint32).view(dtype=numpy.uint8)
            #self.footer = numpy.array([0x0ffffffff, 0, 0], dtype=numpy.uint32).view(dtype=numpy.uint8)
        else:
            raise NotImplementedError (`self.record`)

    def get_size(self):
        """ Return total memory size in bytes needed to fit the entry to memory.
        """
        (entry, type_name, label, data) = self.record
        if type_name=='SUBBLOCK':
            if data is None:
                return 12
            size = 0
            for item in data:
                size += item.get_size()
            return 12 + size
        if type_name=='LONG':
            return 12 + 4
        if type_name=='DOUBLE':
            return 12 + 8
        if type_name == 'ASCII':
            return 12 + len(data) + 1
        raise NotImplementedError (`self.record`)

    def toarray(self, target = None):
        if target is None:
            target = numpy.zeros((self.get_size(),), dtype=numpy.uint8)
        (entry, type_name, label, data) = self.record
        target[:12] = self.header
        if type_name=='SUBBLOCK':
            if data is not None:
                n = 12
                for item in data:
                    item.toarray(target[n:])
                    n += item.get_size()
        elif type_name == 'ASCII':
            target[12:12+len(data)+1] = numpy.array([data+'\0']).view (dtype=numpy.uint8)
        elif type_name == 'LONG':
            target[12:12+4] = numpy.array([data], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'DOUBLE':
            target[12:12+8] = numpy.array([data], dtype=numpy.float64).view(dtype=numpy.uint8)
        else:
            raise NotImplementedError (`self.record`)
        return target

    def tostr(self, tab=''):
        (entry, type_name, label, data) = self.record
        if type_name=='SUBBLOCK':
            if data is None:
                return '%s%s' % (tab[:-2], label)
            l = ['%s%s[size=%s]' % (tab, label, self.get_size ())]
            for item in data:
                l.append(item.tostr(tab=tab+'  '))
            return '\n'.join (l)
        return '%s%s = %r' % (tab, label, data)

    __str__ = tostr

    def append (self, entry):
        assert self.record[1]=='SUBBLOCK',`self.record`
        self.record[3].append(entry)


class IFDEntry:

    def __init__(self, tiff, offset):
        self.tiff = tiff
        self.tag = tiff.get_uint16(offset)
        self.type = tiff.get_uint16(offset+2)
        self.count = tiff.get_uint32(offset+4)
        if self.tag==lsmtag:
            self.type = lsmtype
            type2bytes[lsmtype] = self.count
            self.count = 1

        bytes = type2bytes.get(self.type,0)
        if self.count==1 and 1<=bytes<=4:
            value = tiff.get_value(offset+8, self.type)
        else:
            self.offset = tiff.get_int32(offset+8)
            value = tiff.get_values(self.offset, self.type, self.count)
        if value is not None:
            self.value = value

        self.tag_name = tag_value2name.get(self.tag,'TAG%s' % (hex(self.tag)))
        self.type_name = type2name.get(self.type, 'TYPE%s' % (self.type))
        
    def __str__(self):
        if hasattr(self, 'value'):
            return 'IFD(tag=%(tag_name)s, value=%(value)r)' % (self.__dict__)
        else:
            return 'IFD(tag=%(tag_name)s, type=%(type_name)s, count=%(count)s, offset=%(offset)s)' % (self.__dict__)

    def get_lsm_scaninfo(self):
        """
        Return LSM scan information.

        Returns
        -------
        record : Record
        """
        n = n1 = self.value['OffsetScanInformation'][0]
        record = None
        tab = ' '
        while 1:
            entry, type, size = self.tiff.get_values(n, 'LONG', 3)
            n += 12
            label, type_name = lsm.scaninfo.get(entry, (None, None))
            if label is None:
                type_name = {0:'SUBBLOCK', 2:'ASCII', 4:'LONG', 5:'DOUBLE'}.get(type)
                if type_name is None:
                    raise NotImplementedError(`hex (entry), type, size`)
                label = 'ENTRY%s' % (hex(entry))
                lsm.scaninfo[entry] = label, type_name
            if type_name=='SUBBLOCK':
                assert type==0,`hex (entry), type, size`
                if label == 'end':
                    entry = Entry(entry, type_name, label, None)
                    record.append(entry)
                    if record.parent is None:
                        break
                    record.parent.append(record)
                    record = record.parent
                else:
                    prev_record = record
                    record = Entry(entry, type_name, label, [])
                    record.parent = prev_record
                assert size==0,`hex (entry), type, size`
                continue
            if type_name=='ASCII':
                assert type==2,`hex (entry), type, size`
                value = self.tiff.get_string (n, size-1)
            elif type_name=='LONG':
                assert type==4,`hex (entry), type, size`
                value = self.tiff.get_long(n)
            elif type_name=='DOUBLE':
                assert type==5,`hex (entry), type, size`
                value = self.tiff.get_double(n)
            else:
                raise NotImplementedError(`hex (entry), type, size`)
            entry = Entry(entry, type_name, label, value)
            n += size
            record.append(entry)

        print n - n1
        return record
            
def main ():
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        raise ValueError('File %r does not exists' % (filename))

    t = TIFFView(filename)

    for IFD in t.iter_IFD():
        print IFD

    record = IFD.get_lsm_scaninfo()
    print record
    print record.get_size ()
    print record.toarray().view (numpy.uint16)

if __name__ == '__main__':
    main()


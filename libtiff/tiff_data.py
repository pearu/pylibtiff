"""
Defines data for TIFF manipulations.

"""

__all__ = ['type2name', 'name2type', 'type2bytes', 'type2dtype',
           'tag_value2name', 'tag_name2value', 'tag_value2type',
           'LittleEndianNumpyDTypes', 'BigEndianNumpyDTypes',
           'default_tag_values', 'sample_format_map']

import numpy

# <TagName> <Hex> <Type> <Number of values>
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
  TopLeft 1
  TopRight 2
  BottomRight 3
  BottomLeft 4
  LeftTop 5
  RightTop 6
  RightBottom 7
  LeftBottom 8
SamplesPerPixel 115 SHORT 1
RowsPerStrip 116 SHORT|LONG 1
StripByteCounts 117 LONG|SHORT StripsPerImage
MinSampleValue 118 SHORT SamplesPerPixel
MaxSampleValue 119 SHORT SamplesPerPixel
XResolution 11A RATIONAL 1
YResolution 11B RATIONAL 1
PlanarConfiguration 11C SHORT 1
  Chunky 1
  Planar 2
PageName 11D ASCII
XPosition 11E DOUBLE
YPosition 11F DOUBLE
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
InkNames 14D ASCII <total number of chars in all ink name strings, including zeros>  # noqa: E501
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

# EXIF tags, see
# http://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif.html
EXIF_IFDOffset 8769 SHORT 1
EXIF_ExposureTime 829a RATIONAL 1
EXIF_FNumber 829d RATIONAL 1
EXIF_ExposureProgram 8822 SHORT 1
EXIF_SpectralSensitivity 8824 ASCII
EXIF_ISOSpeedRatings 8827 SHORT 1
EXIF_OECF 8828 UNDEFINED
EXIF_ExifVersion 9000 UNDEFINED 4
EXIF_DateTimeOriginal 9003 ASCII
EXIF_DateTimeDigitized 9004 ASCII
EXIF_ComponentsConfiguration 9101 UNDEFINED 4
EXIF_CompressedBitsPerPixel 9102 RATIONAL 1
EXIF_ShutterSpeedValue 9201 SRATIONAL 1
EXIF_ApertureValue 9202 RATIONAL 1
EXIF_BrightnessValue 9203 SRATIONAL 1
EXIF_ExposureBiasValue 9204 SRATIONAL 1
EXIF_MaxApertureValue 9205 RATIONAL 1
EXIF_SubjectDistance 9206 RATIONAL 1
EXIF_MeteringMode 9207 SHORT 1
EXIF_LightSource 9208 SHORT 1
EXIF_Flash 9209 SHORT 1
EXIF_FocalLength 920a RATIONAL 1
EXIF_SubjectArea 9214 SHORT 2|3|4
EXIF_MakerNote 927c UNDEFINED
EXIF_UserComment 9286 UNDEFINED
EXIF_SubsecTime 9290 ASCII
EXIF_SubsecTimeOriginal 9291 ASCII
EXIF_SubsecTimeDigitized 9292 ASCII
EXIF_FlashpixVersion a000 UNDEFINED 4
EXIF_ColorSpace a001 SHORT 1
EXIF_PixelXDimension a002 SHORT!LONG 1
EXIF_PixelYDimension a003 SHORT!LONG 1
EXIF_RelatedSoundFile a004 ASCII 13
EXIF_FlashEnergy a20b RATIONAL 1
EXIF_SpatialFrequencyResponse a20c UNDEFINED
EXIF_FocalPlaneXResolution a20e RATIONAL 1
EXIF_FocalPlaneYResolution a20f RATIONAL 1
EXIF_FocalPlaneResolutionUnit a210 SHORT 1
EXIF_SubjectLocation a214 SHORT 2
EXIF_ExposureIndex a215 RATIONAL 1
EXIF_SensingMethod a217 SHORT 1
EXIF_FileSource a300 UNDEFINED 1
EXIF_SceneType a301 UNDEFINED 1
EXIF_CFAPattern a302 UNDEFINED
EXIF_CustomRendered a401 SHORT 1
EXIF_ExposureMode a402 SHORT 1
EXIF_WhiteBalance a403 SHORT 1
EXIF_DigitalZoomRatio a404 RATIONAL 1
EXIF_FocalLengthIn35mmFilm a405 SHORT 1
EXIF_SceneCaptureType a406 SHORT 1
EXIF_GainControl a407 SHORT 1
EXIF_Contrast a408 SHORT 1
EXIF_Saturation a409 SHORT 1
EXIF_Sharpness a40a SHORT 1
EXIF_DeviceSettingDescription a40b UNDEFINED
EXIF_SubjectDistanceRange a40c SHORT 1
EXIF_ImageUniqueID a420 ASCII 33

'''

default_tag_values = dict(BitsPerSample=8, SampleFormat=1,
                          RowsPerStrip=2**32 - 1,
                          SamplesPerPixel=1, ExtraSamples=None,
                          PlanarConfiguration=1,
                          Compression=1, Predictor=1,
                          NewSubfileType=0,
                          Orientation=1,
                          MaxSampleValue=None, MinSampleValue=None,
                          DateTime=None,
                          Artist=None,
                          HostComputer=None,
                          Software=None,
                          ImageDescription=None,
                          DocumentName=None,
                          ResolutionUnit=2, XResolution=1, YResolution=1,
                          FillOrder=1,
                          XPosition=None, YPosition=None,
                          Make=None, Model=None, Copyright=None,)

rational = numpy.dtype([('numer', numpy.uint32), ('denom', numpy.uint32)])
srational = numpy.dtype([('numer', numpy.int32), ('denom', numpy.int32)])

type2name = {1: 'BYTE', 2: 'ASCII', 3: 'SHORT', 4: 'LONG', 5: 'RATIONAL',
             # two longs, lsm uses it for float64
             6: 'SBYTE', 7: 'UNDEFINED', 8: 'SSHORT', 9: 'SLONG',
             10: 'SRATIONAL',
             11: 'FLOAT', 12: 'DOUBLE',
             }
name2type = dict((v, k) for k, v in list(type2name.items()))
name2type['SHORT|LONG'] = name2type['LONG']
name2type['LONG|SHORT'] = name2type['LONG']
type2bytes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4,
              10: 8, 11: 4, 12: 8}
type2dtype = {1: numpy.uint8, 2: numpy.uint8, 3: numpy.uint16, 4: numpy.uint32,
              5: rational, 6: numpy.int8, 8: numpy.int16, 9: numpy.int32,
              10: srational, 11: numpy.float32, 12: numpy.float64}

tag_value2name = {}
tag_name2value = {}
tag_value2type = {}
for line in tag_info.split('\n'):
    if not line or line.startswith('#'):
        continue
    if line[0] == ' ':
        pass
    else:
        n, h, t = line.split()[:3]
        h = eval('0x' + h)
        tag_value2name[h] = n
        tag_value2type[h] = t
        tag_name2value[n] = h

sample_format_map = {1: 'uint', 2: 'int', 3: 'float', None:
                     'uint', 6: 'complex'}


class NumpyDTypes:

    def get_dtype(self, sample_format, bits_per_sample):
        format = sample_format_map[sample_format]
        dtypename = '%s%s' % (format, bits_per_sample)
        return getattr(self, dtypename)


class LittleEndianNumpyDTypes(NumpyDTypes):
    uint8 = numpy.dtype('<u1')
    uint16 = numpy.dtype('<u2')
    uint32 = numpy.dtype('<u4')
    uint64 = numpy.dtype('<u8')
    int8 = numpy.dtype('<i1')
    int16 = numpy.dtype('<i2')
    int32 = numpy.dtype('<i4')
    int64 = numpy.dtype('<i8')
    float32 = numpy.dtype('<f4')
    float64 = numpy.dtype('<f8')
    complex64 = numpy.dtype('<c8')
    complex128 = numpy.dtype('<c16')

    @property
    def type2dt(self):
        return dict((k, numpy.dtype(v).newbyteorder('<'))
                    for k, v in list(type2dtype.items()))


LittleEndianNumpyDTypes = LittleEndianNumpyDTypes()


class BigEndianNumpyDTypes(NumpyDTypes):
    uint8 = numpy.dtype('>u1')
    uint16 = numpy.dtype('>u2')
    uint32 = numpy.dtype('>u4')
    uint64 = numpy.dtype('>u8')
    int8 = numpy.dtype('>i1')
    int16 = numpy.dtype('>i2')
    int32 = numpy.dtype('>i4')
    int64 = numpy.dtype('>i8')
    float32 = numpy.dtype('>f4')
    float64 = numpy.dtype('>f8')
    complex64 = numpy.dtype('>c8')
    complex128 = numpy.dtype('>c16')

    @property
    def type2dt(self):
        return dict((k, numpy.dtype(v).newbyteorder('>'))
                    for k, v in list(type2dtype.items()))


BigEndianNumpyDTypes = BigEndianNumpyDTypes()

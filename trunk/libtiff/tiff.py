"""
tiff - implements a numpy.memmap based TIFF file reader and writer
allowing manipulating TIFF files that have sizes larger than
available memory in computer.

Usage:
>>> tiff = TIFFfile('<filename.(tif|lsm)>')
>>> samples, sample_name = tiff.get_samples()

>>> tiff = TIFFimage(data, description=<str>)
>>> tiff.write_file (<filename.tif>, compression='none'|'lzw')
>>> del tiff # flush data to disk
"""
# Author: Pearu Peterson
# Created: April 2010
from __future__ import division
__all__ = ['TIFFfile', 'TIFFimage']

import os
import sys
import time
import numpy

import lzw

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
name2type['SHORT|LONG'] = name2type['LONG']
name2type['LONG|SHORT'] = name2type['LONG']
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
IFDEntry_finalize_hooks = []

# Register CZ LSM support:
import lsm
lsm.register(locals())

class TIFFentry:
    """ Hold a IFD entry used by TIFFimage.
    """
    
    def __init__ (self, tag):
        if isinstance(tag, str):
            tag = tag_name2value[tag]
        assert isinstance (tag, int), `tag`
        self.tag = tag
        self.type_name = tag_value2type[tag]
        self.type = name2type[self.type_name]
        self.type_nbytes = type2bytes[self.type]
        self.type_dtype = type2dtype[self.type]
        self.tag_name = tag_value2name.get(self.tag,'TAG%s' % (hex(self.tag),))

        self.record = numpy.zeros((12,), dtype=numpy.ubyte)
        self.record[:2].view(dtype=numpy.uint16)[0] = self.tag
        self.record[2:4].view(dtype=numpy.uint16)[0] = self.type
        self.values = []

    def __str__(self):
        return '%s(entry=(%s,%s,%s,%s))' % (self.__class__.__name__, self.tag_name, self.type_name, self.count, self.offset)
    __repr__ = __str__

    @property
    def count(self):
        return self.record[4:8].view(dtype=numpy.uint32)

    @property
    def offset(self):
        return self.record[8:12].view(dtype=numpy.uint32)

    @property
    def nbytes(self):
        if self.offset_is_value:
            return 0
        return self.count[0] * self.type_nbytes

    @property
    def offset_is_value (self):
        return not self.values and self.count[0]==1 and self.type_nbytes<=4 and self.type_name!='ASCII'

    def __getitem__ (self, index):
        if self.offset_is_value:
            if index>0:
                raise IndexError(`index`)
            return self.offset[0]
        return self.values[index]

    def add_value(self, value):
        if self.type_name=='ASCII':
            value = str(value)
            if self.count[0]==0:
                self.values.append(value)
            else:
                self.values[0] += value
            self.count[0] = len(self.values[0]) + 1
        elif self.type_nbytes<=4:
            self.count[0] += 1
            if self.count[0]==1:
                self.offset[0] = value
            elif self.count[0]==2:
                self.values.append(self.offset[0])
                self.values.append(value)
                self.offset[0] = 0
            else:
                self.values.append(value)
        else:
            self.count[0] += 1
            self.values.append(value)

    def set_value (self, value):
        assert self.type_name!='ASCII',`self`
        if self.count[0]:
            self.count[0] -= 1
            if self.values:
                del self.values[-1]
        self.add_value (value)

    def set_offset(self, offset):
        self.offset[0] = offset

    def toarray(self, target = None):
        if self.offset_is_value:
            return
        if target is None:
            target = numpy.zeros((self.nbytes,), dtype=numpy.ubyte)
        dtype = target.dtype
        offset = 0
        if self.type_name=='ASCII':
            data = numpy.array([self.values[0] + '\0']).view(dtype=numpy.ubyte)
            target[offset:offset+self.nbytes] = data
        else:
            for value in self.values:
                dtype = self.type_dtype
                if self.type_name=='RATIONAL' and isinstance(value, (int, long, float)):
                    dtype = numpy.float64
                target[offset:offset + self.type_nbytes].view(dtype=dtype)[0] = value
                offset += self.type_nbytes
        return target

class TIFFimage:
    """
    Hold an image stack that can be written to TIFF file.
    """

    def __init__(self, data, description=''):
        """
        data : {list, numpy.ndarray}
          Specify image data as a list of images or as an array with rank<=3.
        """
        dtype = None
        if isinstance(data, list):
            image = data[0]
            self.width, self.length = image.shape
            self.depth = len(data)
            dtype = image.dtype
        elif isinstance(data, numpy.ndarray):
            shape = data.shape
            dtype = data.dtype
            if len (shape)==1:
                self.length, = shape
                self.width = 1
                self.depth = 1
                data = [[data]]
            elif len (shape)==2:
                self.width, self.length = shape
                self.depth = 1
                data = [data]
            elif len (shape)==3:
                self.depth, self.width, self.length = shape
            else:
                raise NotImplementedError (`shape`)
        else:
            raise NotImplementedError (`type (data)`)
        self.data = data
        self.dtype = dtype
        self.description = description

    def write_file(self, filename, compression='none',
                   strip_size = 2**13):
        """
        Write image data to TIFF file.

        Parameters
        ----------
        filename : str
        compression : {'none', 'lzw'}
        strip_size : int
          Specify the size of uncompressed strip.
        """
        if os.path.splitext (filename)[1].lower () not in ['.tif', '.tiff']:
            filename = filename + '.tif'

        sys.stdout.write('Writing TIFF records to %s\n' % (filename))
        sys.stdout.flush ()

        compression_map = dict(packbits=32773, none=1, lzw=5, jpeg=6, ccitt1d=2,
                               group3fax = 3, group4fax = 4
                               )
        compress_map = dict(none=lambda data: data,
                            lzw = lzw.encode_array)
        compress = compress_map.get(compression, None)
        if compress is None:
            raise NotImplementedError (`compression`)

        # compute tif file size and create image file directories data
        image_directories = []
        total_size = 8
        data_size = 0
        image_data_size = 0
        for i,image in enumerate(self.data):
            sys.stdout.write('\r  creating records: %5s%% done  ' % (int(100.0*i/len(self.data))))
            sys.stdout.flush ()

            sample_format = dict (u=1,i=2,f=3).get(image.dtype.kind, 4)
            length, width = image.shape
            bytes_per_row = width * image.dtype.itemsize
            rows_per_strip = int(numpy.ceil(strip_size / bytes_per_row))
            strips_per_image = int(numpy.floor((length + rows_per_strip - 1) / rows_per_strip))
            assert bytes_per_row * rows_per_strip * strips_per_image >= image.nbytes

            d = dict(ImageWidth=width,
                     ImageLength=length,
                     Compression=compression_map.get (compression, 1),
                     PhotometricInterpretation=1,
                     PlanarConfiguration=1,
                     Orientation=1,
                     ResolutionUnit = 1,
                     XResolution = 1,
                     YResolution = 1,
                     SamplesPerPixel = 1,
                     RowsPerStrip = rows_per_strip,
                     BitsPerSample = image.dtype.itemsize * 8,
                     SampleFormat = sample_format,
                     )
            if i==0:
                d.update(dict(
                        ImageDescription = self.description,
                        Software = 'http://code.google.com/p/pylibtiff/'))

            entries = []
            for tagname, value in d.items ():
                entry = TIFFentry(tagname)
                entry.add_value(value)
                entries.append(entry)
                total_size += 12 + entry.nbytes
                data_size += entry.nbytes

            strip_byte_counts = TIFFentry('StripByteCounts')
            strip_offsets = TIFFentry('StripOffsets')
            entries.append(strip_byte_counts)
            entries.append(strip_offsets)
            # strip_offsets and strip_byte_counts will be filled in the next loop
            if strips_per_image==1:
                assert strip_byte_counts.type_nbytes <= 4
                assert strip_offsets.type_nbytes <= 4
                total_size += 2*12
            else:
                total_size += 2*12 + strips_per_image*(strip_byte_counts.type_nbytes + strip_offsets.type_nbytes)
                data_size += strips_per_image * (strip_byte_counts.type_nbytes + strip_offsets.type_nbytes)
            
            # image data:
            total_size += image.nbytes
            data_size += image.nbytes
            image_data_size += image.nbytes

            # records for nof IFD entries and offset to the next IFD:
            total_size += 2 + 4

            # entries must be sorted by tag number
            entries.sort(cmp=lambda x,y: cmp(x.tag, y.tag))

            strip_info = strip_offsets, strip_byte_counts, strips_per_image, rows_per_strip, bytes_per_row
            image_directories.append((entries, strip_info, image))

        tif = numpy.memmap(filename, dtype=numpy.ubyte, mode='w+', shape=(total_size,))
        # write TIFF header
        tif[:2].view(dtype=numpy.uint16)[0] = 0x4949 # low-endian
        tif[2:4].view (dtype=numpy.uint16)[0] = 42   # magic number
        tif[4:8].view (dtype=numpy.uint32)[0] = 8    # offset to the first IFD

        offset = 8
        data_offset = total_size - data_size
        image_data_offset = total_size - image_data_size
        first_data_offset = data_offset
        first_image_data_offset = image_data_offset
        start_time = time.time ()
        for i, (entries, strip_info, image) in enumerate(image_directories):
            strip_offsets, strip_byte_counts, strips_per_image, rows_per_strip, bytes_per_row = strip_info
            sys.stdout.write('\r  filling records: %5s%% done (%.2f Mbytes/s)' % (int(100.0*i/len (image_directories)), 
                                                                                (image_data_offset-first_image_data_offset)/(time.time ()-start_time)/1024**2))
            sys.stdout.flush ()

            # write the nof IFD entries
            tif[offset:offset+2].view(dtype=numpy.uint16)[0] = len(entries)
            offset += 2
            assert offset <= first_data_offset,`offset, first_data_offset`

            # write image data
            data = image.view(dtype=numpy.ubyte).reshape((image.nbytes,))
            
            for j in range(strips_per_image):
                c = rows_per_strip * bytes_per_row
                k = j * c
                c -= max((j+1) * c - image.nbytes, 0)
                assert c>0,`c`
                strip = compress(data[k:k+c])
                strip_offsets.add_value(image_data_offset)
                strip_byte_counts.add_value(strip.nbytes)
                tif[image_data_offset:image_data_offset+strip.nbytes] = strip
                image_data_offset += strip.nbytes
                if j==0:
                    first = strip_offsets[0]
                last = strip_offsets[-1] + strip_byte_counts[-1]

            # write IFD entries
            for entry in entries:
                data_size = entry.nbytes
                if data_size:
                    entry.set_offset(data_offset)
                    assert data_offset+data_size <= total_size, `data_offset+data_size,total_size`
                    r = entry.toarray(tif[data_offset:data_offset + data_size])
                    assert r.nbytes==data_size
                    data_offset += data_size
                    assert data_offset <= first_image_data_offset,`data_offset, first_image_data_offset, i`
                tif[offset:offset+12] = entry.record
                offset += 12
                assert offset <= first_data_offset,`offset, first_data_offset, i`

            # write offset to the next IFD
            tif[offset:offset+4].view(dtype=numpy.uint32)[0] = offset + 4
            offset += 4
            assert offset <= first_data_offset,`offset, first_data_offset`

        # last offset must be 0
        tif[offset-4:offset].view(dtype=numpy.uint32)[0] = 0
        sys.stdout.write ('\r'+70*' ')
        sys.stdout.write ('\r  flushing records (%s Mbytes) to disk... ' % (round(total_size/(1024*1024)))); sys.stdout.flush ()
        del tif
        sys.stdout.write ('done\n'); sys.stdout.flush ()        


class TIFFfile:
    """
    Hold a TIFF file image stack that is accessed via memmap.

    Attributes
    ----------
    filename : str
    data : memmap
    IFD : IFD-list
    """

    def __init__(self, filename, mode='r', first_byte = 0):
        if mode!='r':
            raise NotImplementedError(`mode`)
        self.filename = filename
        self.first_byte = first_byte
        self.data = numpy.memmap(filename, dtype=numpy.ubyte, mode=mode)
        self.init_reader()

    def init_reader(self):

        first_byte = self.first_byte
        self.memory_usage = [(self.data.nbytes, self.data.nbytes, 'eof')]
        byteorder = self.get_uint16(first_byte)
        if byteorder==0x4949:
            self.endian = 'little'
        elif byteorder==0x4d4d:
            self.endian = 'big'
        else:
            raise ValueError('unrecognized byteorder: %s' % (hex(byteorder)))
        magic = self.get_uint16(first_byte+2)
        if magic!=42:
            raise ValueError('wrong magic number for TIFF file: %s' % (magic))
        self.IFD0 = IFD0 = first_byte + self.get_uint32(first_byte+4)
        self.memory_usage.append((first_byte, first_byte+8, 'file header'))
        n = self.get_uint16(IFD0)
        IFD_list = []
        IFD_offset = IFD0
        while IFD_offset:
            n = self.get_uint16(IFD_offset)
            ifd = IFD(self)
            for i in range(n):
                entry = IFDEntry(ifd, self, IFD_offset + 2 + i*12)
                ifd.append(entry)
            #print ifd
            ifd.finalize()
            IFD_list.append(ifd)
            self.memory_usage.append((IFD_offset, IFD_offset + 2 + n*12 + 4, 'IFD%s entries (%s)' % (len(IFD_list), len(ifd))))
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

    def check_memory_usage(self, verbose=True):
        ''' Check memory usage of TIFF fields and blocks.

        Returns
        -------
        ok : bool
          Return False if unknown or overlapping memory areas have been detected.
        '''
        l = []
        l.extend(self.memory_usage)
        for ifd in self.IFD:
            l.extend(ifd.memory_usage)
        l.sort()
        last_end = None
        ok = True
        for start, end, resource in l:
            if last_end:
                if last_end!=start:
                    if verbose:
                        print '--- unknown %s bytes' % (start-last_end)
                    ok = False
                    if start<last_end and verbose:
                        print '--- overlapping memory area'
            if verbose:
                print '%s..%s[%s] contains %s' % (start, end,end-start, resource)
            last_end = end
        return ok

    def is_contiguous(self):
        for i,ifd in enumerate(self.IFD):
            strip_offsets = ifd.get('StripOffsets').value
            strip_nbytes = ifd.get('StripByteCounts').value
            if not ifd.is_contiguous():
                return False
            if i==0:
                pass
            else:
                if isinstance(strip_offsets, numpy.ndarray):
                    start = strip_offsets[0]
                else:
                    start = strip_offsets
                if end!=start:
                    return False
            if isinstance(strip_offsets, numpy.ndarray):
                end = strip_offsets[-1] + strip_nbytes[-1]
            else:
                end = strip_offsets + strip_nbytes
        return True

    def get_contiguous(self):
        """ Return memmap of a stack of images.
        """
        if not self.is_contiguous ():
            raise ValueError('Image stack data not contiguous')
        ifd0 = self.IFD[0]
        ifd1 = self.IFD[-1]
        width = ifd0.get ('ImageWidth').value
        length = ifd0.get ('ImageLength').value
        assert width == ifd1.get ('ImageWidth').value
        assert length == ifd1.get ('ImageLength').value
        depth = len(self.IFD)
        compression = ifd.get('Compression').value
        if compression!=1:
            raise ValueError('Unable to get contiguous image stack from compressed data')            
        bits_per_sample = ifd0.get('BitsPerSample').value
        photo_interp = ifd0.get('PhotometricInterpretation').value
        planar_config = ifd0.get('PlanarConfiguration').value        
        strip_offsets0 = ifd0.get('StripOffsets').value
        strip_nbytes0 = ifd0.get('StripByteCounts').value
        strip_offsets1 = ifd1.get('StripOffsets').value
        strip_nbytes1 = ifd1.get('StripByteCounts').value
        samples_per_pixel = ifd1.get('SamplesPerPixel').value
        assert samples_per_pixel==1,`samples_per_pixel`

        if isinstance (bits_per_sample, numpy.ndarray):
            dtype = getattr (numpy, 'uint%s' % (bits_per_sample[i]))
        else:
            dtype = getattr (numpy, 'uint%s' % (bits_per_sample))

        if isinstance(strip_offsets0, numpy.ndarray):
            start = strip_offsets0[0]
            end = strip_offsets1[-1] + strip_nbytes1[-1]
        else:
            start = strip_offsets0
            end = strip_offsets1 + strip_nbytes1
        return self.data[start:end].view (dtype=dtype).reshape ((depth, width, length))

    def get_samples(self, subfile_type=0, verbose=False):
        """
        Return samples and sample names.

        Parameters
        ----------
        subfile_type : {0, 1}
          Specify subfile type. Subfile type 1 corresponds to reduced resolution image.
        verbose : bool
          When True the print out information about samples

        Returns
        -------
        samples : list
          List of numpy.memmap arrays of samples
        sample_names : list
          List of the corresponding sample names
        """
        l = []
        i = 0
        step = 0
        for ifd in self.IFD:
            sft = ifd.get('NewSubfileType')
            if sft is not None and sft.value!=subfile_type:
                continue
            if not ifd.is_contiguous():
                raise NotImplementedError('not contiguous strips')
            compression = ifd.get('Compression').value
            if compression!=1:
                raise ValueError('Unable to get contiguous samples from compressed data')            
            strip_offsets = ifd.get('StripOffsets').value
            strip_nbytes = ifd.get('StripByteCounts').value
            if isinstance(strip_offsets, numpy.ndarray):
                l.append((strip_offsets[0], strip_offsets[-1]+strip_nbytes[-1]))
            else:
                l.append((strip_offsets, strip_offsets+strip_nbytes))
            if i==0:
                width = ifd.get ('ImageWidth').value
                length = ifd.get ('ImageLength').value
                samples_per_pixel = ifd.get('SamplesPerPixel').value
                planar_config = ifd.get('PlanarConfiguration').value
                bits_per_sample = ifd.get('BitsPerSample').value
                if isinstance (bits_per_sample, numpy.ndarray):
                    dtype_lst = [getattr (numpy, 'uint%s' % (bits_per_sample[j])) for j in range(len(bits_per_sample))]
                else:
                    dtype_lst = [getattr (numpy, 'uint%s' % (bits_per_sample))]
                strip_length = l[-1][1] - l[-1][0]
                if verbose:
                    print '''
width : %(width)s
length : %(length)s
samples_per_pixel : %(samples_per_pixel)s
planar_config : %(planar_config)s
bits_per_sample : %(bits_per_sample)s
strip_length : %(strip_length)s
''' % (locals ())

            else:
                assert width == ifd.get ('ImageWidth').value, `width, ifd.get ('ImageWidth').value`
                assert length == ifd.get ('ImageLength').value,` length,  ifd.get ('ImageLength').value`
                assert samples_per_pixel == ifd.get('SamplesPerPixel').value, `samples_per_pixel, ifd.get('SamplesPerPixel').value`
                assert planar_config == ifd.get('PlanarConfiguration').value
                assert strip_length == l[-1][1] - l[-1][0]
                if isinstance (bits_per_sample, numpy.ndarray):
                    assert (bits_per_sample == ifd.get('BitsPerSample').value).all(),`bits_per_sample, ifd.get('BitsPerSample').value`
                else:
                    assert (bits_per_sample == ifd.get('BitsPerSample').value),`bits_per_sample, ifd.get('BitsPerSample').value`
            if i>0:
                if i==1:
                    step = l[-1][0] - l[-2][1]
                    assert step>=0,`step, l[-2], l[-1]`
                else:
                    assert step == l[-1][0] - l[-2][1],`step, l[-2], l[-1]`
            i += 1
        assert i>=0,`i`
        depth = i
        start = l[0][0]
        end = l[-1][1]
        sample_names = ['sample%s' % (j) for j in range (samples_per_pixel)]

        if start > step:
            arr = self.data[start - step: end].reshape((depth, strip_length + step))
            k = step
        elif end <= self.data.size - step:
            arr = self.data[start: end+step].reshape((depth, strip_length + step))
            k = 0
        else:
            raise NotImplementedError (`start, end, step`)
        if planar_config==2:
            if self.is_lsm:
                # LSM510: one strip per image plane channel
                if subfile_type==0:
                    sample_names = self.lsminfo.get('data channel name')
                elif subfile_type==1:
                    sample_names = ['red', 'green', 'blue']
                    assert samples_per_pixel==3,`samples_per_pixel`
                else:
                    raise NotImplementedError (`subfile_type`)
                samples = []
                if isinstance(bits_per_sample, numpy.ndarray):
                    for j in range(samples_per_pixel):
                        bytes = bits_per_sample[j] // 8 * width * length
                        samples.append(arr[:,k:k+bytes].reshape((depth, width, length)))
                        k += bytes
                else:
                    assert samples_per_pixel==1,`samples_per_pixel, bits_per_sample`
                    bytes = bits_per_sample // 8 * width * length
                    samples.append(arr[:,k:k+bytes].reshape((depth, width, length)))
                return samples, sample_names
            raise NotImplementedError (`planar_config, self.is_lsm`)
        elif planar_config==1:
            samples = []
            if isinstance(bits_per_sample, numpy.ndarray):
                bytes = sum(bits_per_sample[:samples_per_pixel]) // 8 * width * length
            else:
                bytes = bits_per_sample // 8 * width * length
            for j in range(samples_per_pixel):
                samples.append(arr[:,k+j:k+j+bytes:samples_per_pixel].reshape((depth, width, length)))
                k += bytes
            return samples, sample_names
        else:
            raise NotImplementedError (`planar_config`)

class IFD:
    """ Image File Directory data structure.

    Attributes
    ----------
    entries : IFDEntry-list
    """
    def __init__(self, tiff):
        self.tiff = tiff
        self.entries = []

    def __len__ (self):
        return len (self.entries)

    def append(self, entry):
        self.entries.append(entry)

    @property
    def memory_usage(self):
        l = []
        for entry in self.entries:
            l.extend(entry.memory_usage)
        return l

    def __str__(self):
        l = []
        for entry in self.entries:
            l.append(str (entry))
        return '\n'.join(l)

    def get(self, tag_name):
        """Return IFD entry with given tag name.
        """
        for entry in self.entries:
            if entry.tag_name==tag_name:
                return entry

    def finalize(self):
        for entry in self.entries:
            for hook in IFDEntry_finalize_hooks:
                hook(entry)

    def is_contiguous (self):
        strip_offsets = self.get('StripOffsets').value
        strip_nbytes = self.get('StripByteCounts').value
        if isinstance(strip_offsets, numpy.ndarray):
            for i in range (len(strip_offsets)-1):
                if strip_offsets[i] + strip_nbytes[i] != strip_offsets[i+1]:
                    return False
        return True

    def get_contiguous(self, channel_name=None):
        """ Return memmap of an image.

        This operation is succesful only when image data strips are
        contiguous in memory. Return None when unsuccesful.
        """
        width = self.get ('ImageWidth').value
        length = self.get ('ImageLength').value
        strip_offsets = self.get('StripOffsets').value
        strip_nbytes = self.get('StripByteCounts').value
        bits_per_sample = self.get('BitsPerSample').value
        photo_interp = self.get('PhotometricInterpretation').value
        planar_config = self.get('PlanarConfiguration').value
        compression = self.get('Compression').value
        subfile_type = self.get('NewSubfileType').value
        if compression != 1:
            raise ValueError('Unable to get contiguous image from compressed data')
        if not self.is_contiguous ():
            raise ValueError('Image data not contiguous')

        if self.tiff.is_lsm:
            lsminfo = self.tiff.lsminfo
            #print lsminfo
            if subfile_type==0:
                channel_names = lsminfo.get('data channel name')
            elif subfile_type==1: # thumbnails
                if photo_interp==2:
                    channel_names = 'rgb'
                else:
                    raise NotImplementedError (`photo_interp`)
            else:
                raise NotImplementedError (`subfile_type`)
            assert planar_config==2,`planar_config`
            nof_channels = self.tiff.lsmentry['DimensionChannels'][0]
            scantype = self.tiff.lsmentry['ScanType'][0]
            assert scantype==0,`scantype` # xyz-scan
            r = {}
            for i in range (nof_channels):
                if isinstance (bits_per_sample, numpy.ndarray):
                    dtype = getattr (numpy, 'uint%s' % (bits_per_sample[i]))
                    r[channel_names[i]] = self.tiff.data[strip_offsets[i]:strip_offsets[i]+strip_nbytes[i]].view (dtype=dtype).reshape((width, length))
                else:
                    dtype = getattr (numpy, 'uint%s' % (bits_per_sample))
                    r[channel_names[i]] = self.tiff.data[strip_offsets:strip_offsets+strip_nbytes].view (dtype=dtype).reshape((width, length))
            return r
        else:
            raise NotImplementedError (`self.tiff`)

class IFDEntry:
    """ Entry for Image File Directory data structure.

    Attributes
    ----------
    ifd : IFD
    tiff : TIFFfile
    tag : uint16
      data tag constant
    tag_name : str
      data tag name
    type : uint16
      data type constant
    type_name : str
      data type name
    count : uint32
      number of data points
    offset : {None, int}
      offset of a tag entry in tiff data array
    value : array
      data array
    bytes : int
      number of bytes in data array
    memory_usage : list of 3-tuples
      (start byte, end byte, name of tag)
    """
    def __init__(self, ifd, tiff, offset):
        self.ifd = ifd
        self.tiff = tiff
        self.offset = offset

        # initialization:
        self.tag = tiff.get_uint16(offset)
        self.type = tiff.get_uint16(offset+2)
        self.count = tiff.get_uint32(offset+4)
        for hook in IFDEntry_init_hooks:
            hook(self)
        
        self.bytes = bytes = type2bytes.get(self.type,0)
        if self.count==1 and 1<=bytes<=4:
            self.offset = None
            value = tiff.get_value(offset+8, self.type)
        else:
            self.offset = tiff.get_int32(offset+8)
            value = tiff.get_values(self.offset, self.type, self.count)
        if value is not None:
            self.value = value
        self.tag_name = tag_value2name.get(self.tag,'TAG%s' % (hex(self.tag),))
        self.type_name = type2name.get(self.type, 'TYPE%s' % (self.type,))

        self.memory_usage = []
        if self.offset is not None:
            self.memory_usage.append((self.offset, self.offset + self.bytes*self.count, self.tag_name))
        
    def __str__(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance (r, str):
                return r
        if hasattr(self, 'value'):
            return 'IFDEntry(tag=%(tag_name)s, value=%(value)r, count=%(count)s, offset=%(offset)s)' % (self.__dict__)
        else:
            return 'IFDEntry(tag=%(tag_name)s, type=%(type_name)s, count=%(count)s, offset=%(offset)s)' % (self.__dict__)

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.tiff, self.offset)

def StripOffsets_hook(ifdentry):
    if ifdentry.tag_name=='StripOffsets':
        ifd = ifdentry.ifd
        counts = ifd.get('StripByteCounts')
        if ifdentry.offset is not None:
            for i, (count, offset) in enumerate(zip(counts.value, ifdentry.value)):
                ifdentry.memory_usage.append((offset, offset+count, 'strip %s' % (i)))
        else:
            offset = ifdentry.value
            ifdentry.memory_usage.append((offset, offset+counts.value, 'strip'))

# todo: TileOffsets_hook

IFDEntry_finalize_hooks.append(StripOffsets_hook)

def main ():
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        raise ValueError('File %r does not exists' % (filename))

    t = TIFFfile(filename)

    t.show_memory_usage()

    e = t.IFD[0].entries[-1]
    assert e.is_lsm
    print lsm.lsmblock(e)
    print lsm.lsminfo(e, 0)
    #print lsm.filestructure(e)
    #print lsm.timestamps(e)
    #print lsm.channelwavelength(e)

if __name__ == '__main__':
    main()


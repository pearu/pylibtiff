"""
Provides TIFFfile class.
"""
# Author: Pearu Peterson
# Created: June 2010
from __future__ import division

__all__ = ['TIFFfile']


import sys
import numpy
from numpy.testing.utils import memusage
from .tiff_data import type2name, name2type, type2bytes, type2dtype, tag_value2name, tag_name2value
from .tiff_data import LittleEndianNumpyDTypes, BigEndianNumpyDTypes
from .utils import bytes2str
import lsm
import tif_lzw

IFDEntry_init_hooks = []
IFDEntry_finalize_hooks = []

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

        self.memory_usage = [(self.data.nbytes, self.data.nbytes, 'eof')]
        byteorder = self.data[first_byte:first_byte+2].view(dtype=numpy.uint16)
        if byteorder==0x4949:
            self.endian = 'little'
            self.dtypes = LittleEndianNumpyDTypes
        elif byteorder==0x4d4d:
            self.endian = 'big'
            self.dtypes = BigEndianNumpyDTypes
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
            ifd.finalize()
            IFD_list.append(ifd)
            self.memory_usage.append((IFD_offset, IFD_offset + 2 + n*12 + 4, 'IFD%s entries (%s)' % (len(IFD_list), len(ifd))))
            IFD_offset = self.get_uint32(IFD_offset + 2 + n*12)
        self.IFD = IFD_list

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.filename)

    def get_uint16(self, offset):
        return self.data[offset:offset+2].view(dtype=self.dtypes.uint16)[0]
    def get_uint32(self, offset):
        return self.data[offset:offset+4].view(dtype=self.dtypes.uint32)[0]
    def get_int16(self, offset):
        return self.data[offset:offset+2].view(dtype=self.dtypes.int16)[0]
    def get_int32(self, offset):
        return self.data[offset:offset+4].view(dtype=self.dtypes.int32)[0]
    def get_float32(self, offset):
        return self.data[offset:offset+4].view(dtype=self.dtypes.float32)[0]
    def get_float64(self, offset):
        return self.data[offset:offset+8].view(dtype=self.dtypes.float64)[0]
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
                ntyp = typ
                typ = name2type.get(typ)
            else:
                ntyp = str (typ)
            dtype = self.dtypes.type2dt.get(typ)
            bytes = type2bytes.get(typ)
            if dtype is None or bytes is None:
                sys.stderr.write('get_values: incomplete info for type=%r [%r]: dtype=%s, bytes=%s\n' % (typ,ntyp, dtype, bytes))
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
            dtype = getattr (self.dtypes, 'uint%s' % (bits_per_sample[i]))
        else:
            dtype = getattr (self.dtypes, 'uint%s' % (bits_per_sample))

        if isinstance(strip_offsets0, numpy.ndarray):
            start = strip_offsets0[0]
            end = strip_offsets1[-1] + strip_nbytes1[-1]
        else:
            start = strip_offsets0
            end = strip_offsets1 + strip_nbytes1
        return self.data[start:end].view (dtype=dtype).reshape ((depth, width, length))

    def get_subfile_types(self):
        """ Return a list of subfile types.
        """
        s = set()
        for ifd in self.IFD:
            s.add(ifd.get_value('NewSubfileType', 0))
        return sorted(s)

    def get_depth (self, subfile_type=0):
        depth = 0
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType', 0)==subfile_type:
                depth += 1
        return depth

    def get_info(self, name, index=0, subfile_type=0, default=None):
        """ Return information from the given IFD.
        
        Parameters
        ----------
        name : str
          Specify the name of value. For example, ImageWidth, ImageHeight, etc.
        index : int
          Specify the index of IFD for given subfile_type.
        subfile_type : {0, 1}
          Specify subfile type. Subfile type 1 corresponds to reduced resolution image.

        Returns
        -------
        value : int
        """
        count = 0
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType', subfile_type)==subfile_type:
                if count == index:
                    return ifd.get_value(name, default)
                count += 1
        return default

    def get_sample_names(self, subfile_type=0):
        """ Return a list of sample names (channels).
        """
        samples_per_pixel = self.get_info('SamplesPerPixel', subfile_type=subfile_type, default=1)
        if self.is_lsm:
            if subfile_type==0:
                return self.lsminfo.get('data channel name')
            if subfile_type==1:
                assert samples_per_pixel==3,`samples_per_pixel`
                return ['red', 'green', 'blue']
            raise NotImplementedError (`subfile_type`)
        return ['sample%s' % (j) for j in range (samples_per_pixel)]

    def get_sample_typename(self, subfile_type=0):
        """ Return sample type name.
        """
        bits_per_sample = self.get_info('BitsPerSample', subfile_type=subfile_type, default=8)
        sample_format = self.get_info('SampleFormat', subfile_type=subfile_type, default=1)
        format = {1:'uint', 2:'int', 3:'float', None:'uint', 6:'complex'}.get(sample_format)
        assert format is not None, `sample_format, bits_per_sample`
        if isinstance (bits_per_sample, numpy.ndarray):
            assert len(set (bits_per_sample))==1, `bits_per_sample`
            return '%s%s' % (format, bits_per_sample[0])
        else:
            return '%s%s' % (format, bits_per_sample)

    def get_data_strips(self, subfile_type=0):
        """ Return data location information as a list of tuples.

        Returns
        -------
        strips : list
          List of strips: (offset_start, offset_end, compression, bytes_uncompressed)
        """
        raise
        strips = []
        i = -1
        compression = 1
        rows_per_strip = 2**32-1
        samples_per_pixel = 1
        planar_config = 1
        photometric = 0 # white is zero
        sample_format = 1 # uint
        bits_per_sample = 1
        orientation = 1

        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType', subfile_type) != subfile_type:
                # subfile_type: 0: image, 1: reduced image, 2: single page, 4: transparency mask
                continue
            if not ifd.is_contiguous():
                raise NotImplementedError('none contiguous strips')
            i += 1

            strip_offsets = ifd.get_value('StripOffsets')
            strip_nbytes = ifd.get_value('StripByteCounts') # same size as strip_offsets
            rows_per_strip = ifd.get_value('RowsPerStrip', rows_per_strip)
            compression = ifd.get_value('Compression', compression)
            # 1: topleft, 2: topright, etc
            orientation = ifd.get_value('Orientation', orientation)

            if i==0:
                pixels_per_row = width = ifd.get_value('ImageWidth')
                rows_of_pixels = length = ifd.get_value('ImageLength')

                # 1: RGBRGB..., 2: RR..GG..BB..
                planar_config = ifd.get_value('PlanarConfiguration', planar_config)
                # int
                samples_per_pixel = ifd.get_value('SamplesPerPixel', samples_per_pixel) 
                # None or (samples_per_pixel-3)-array with values: 0 (unspecified), 1 (assocalpha), 2 (unassalpha)
                extra_samples = ifd.get_value('ExtraSamples') 

                if planar_config==1:
                    if isinstance(strip_offsets, numpy.ndarray):
                        strips_per_image = len(strip_offsets)
                    else:
                        strips_per_image = 1
                else: # planar_config==2
                    if isinstance(strip_offsets, numpy.ndarray):
                        strips_per_image = len(strip_offsets) // samples_per_pixel
                    else:
                        assert samples_per_pixel==1, `samples_per_pixel, strip_offsets`
                        strips_per_image = 1

                strips_per_image2 = (length + rows_per_strip - 1)//rows_per_strip
                assert strips_per_image==strips_per_image2,`strips_per_image, strips_per_image2`

                # int or samples_per_pixel-array
                bits_per_sample = ifd.get_value('BitsPerSample', bits_per_sample)

                # int or samples_per_pixel-array with values: 
                #   1: uint, 2: int, 3: float, 4: void, 5: complex int, 6: complex float
                sample_format = ifd.get_value('SampleFormat', sample_format) 

                # 0:WhiteIsZero, 1:BlackIsZero, 2: RGB, 3: Palett, 4: TransparencyMask, 5: CMYK, 
                # 6: YCbCr, 8: CIE L*a*b*, 9: ICC L*a*b*, 10: ITU L*a*b*, 32803: CFA, 
                # 34892: LinearRaw, 32844: Pixar LogL, 32845: Pixar LogLuv
                photometric = ifd.get_value('PhotometricInterpretation', photometric) 

                if isinstance(bits_per_sample, numpy.ndarray):
                    bits_per_pixel = sum(bits_per_sample[:samples_per_pixel])
                else:
                    bits_per_pixel = bits_per_sample
                assert bits_per_pixel % 8 == 0, `bits_per_pixel`
                bytes_per_pixel = bits_per_pixel // 8

                bytes_per_row = pixels_per_row * bytes_per_pixel

            bytes_per_strip = rows_per_strip * bytes_per_row

            if isinstance(strip_offsets, numpy.ndarray):
                for off, nb in zip(strip_offsets, strip_nbytes):
                    strips.append ((off, off+nb, compression, bytes_per_strio))
            else:
                strips.append((strip_offsets, strip_offsets+strip_nbytes, compression, bytes_per_strip))

        return strips

    def get_tiff_array(self, sample_index = 0, subfile_type=0):
        """ Create array of sample images.

        Parameters
        ----------
        sample_index : int
          Specify sample within a pixel.
        subfile_type : int
          Specify TIFF NewSubfileType used for collecting sample images.

        Returns
        -------
        array : TiffArray
          Array of sample images. The array has rank equal to 3.
        """
        from tiff_array import TiffArray, TiffSamplePlane
        planes = []
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType', subfile_type) != subfile_type:
                # subfile_type: 0: image, 1: reduced image, 2: single page, 4: transparency mask
                continue
            planes.append(TiffSamplePlane (ifd, sample_index=sample_index))
        return TiffArray(planes)

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
        can_return_memmap = True
        ifd_lst = [ifd for ifd in self.IFD if ifd.get_value('NewSubfileType', subfile_type)==subfile_type]

        depth = len(ifd_lst)
        full_l = []
        for ifd in ifd_lst:
            if not ifd.is_contiguous():
                raise NotImplementedError('none contiguous strips')

            strip_offsets = ifd.get_value('StripOffsets')
            strip_nbytes = ifd.get_value('StripByteCounts')
            if isinstance(strip_offsets, numpy.ndarray):
                l.append((strip_offsets[0], strip_offsets[-1]+strip_nbytes[-1]))
                for off, nb in zip (strip_offsets, strip_nbytes):
                    full_l.append ((off, off+nb))
            else:
                l.append((strip_offsets, strip_offsets+strip_nbytes))
                full_l.append (l[-1])

            if i==0:
                compression = ifd.get_value('Compression')
                if compression!=1:
                    can_return_memmap = False
                    #raise ValueError('Unable to get contiguous samples from compressed data (compression=%s)' % (compression))            
                width = ifd.get_value('ImageWidth')
                length = ifd.get_value('ImageLength')
                samples_per_pixel = ifd.get_value('SamplesPerPixel', 1)
                planar_config = ifd.get_value('PlanarConfiguration')
                bits_per_sample = ifd.get_value('BitsPerSample')
                sample_format = ifd.get_value('SampleFormat')
                if self.is_lsm or not isinstance(strip_offsets, numpy.ndarray):
                    strips_per_image = 1
                else:
                    strips_per_image = len(strip_offsets)
                format = {1:'uint', 2:'int', 3:'float', None:'uint', 6:'complex'}.get(sample_format)
                if format is None:
                    print 'Warning(TIFFfile.get_samples): unsupported sample_format=%s is mapped to uint' % (sample_format)
                    format = 'uint'

                if isinstance (bits_per_sample, numpy.ndarray):
                    dtype_lst = []
                    bits_per_pixel = 0
                    for j in range(samples_per_pixel):
                        bits = bits_per_sample[j]
                        bits_per_pixel += bits
                        dtype = getattr (self.dtypes, '%s%s' % (format, bits))
                        dtype_lst.append(dtype)
                else:
                    bits_per_pixel = bits_per_sample
                    dtype = getattr (self.dtypes, '%s%s' % (format, bits_per_sample))
                    dtype_lst = [dtype]
                bytes_per_pixel = bits_per_pixel // 8
                assert 8*bytes_per_pixel == bits_per_pixel,`bits_per_pixel`
                bytes_per_row = width * bytes_per_pixel
                strip_length = l[-1][1] - l[-1][0]
                strip_length_str = bytes2str(strip_length)
                bytes_per_image = length * bytes_per_row

                rows_per_strip = bytes_per_image // (bytes_per_row * strips_per_image)
                if bytes_per_image % (bytes_per_row * strips_per_image):
                    rows_per_strip += 1
                assert rows_per_strip == ifd.get_value('RowsPerStrip', rows_per_strip), `rows_per_strip, ifd.get_value('RowsPerStrip'), bytes_per_image, bytes_per_row, strips_per_image, self.filename`
            else:
                assert width == ifd.get_value('ImageWidth', width), `width, ifd.get_value('ImageWidth')`
                assert length == ifd.get_value('ImageLength', length),` length,  ifd.get_value('ImageLength')`
                #assert samples_per_pixel == ifd.get('SamplesPerPixel').value, `samples_per_pixel, ifd.get('SamplesPerPixel').value`
                assert planar_config == ifd.get_value('PlanarConfiguration', planar_config)
                if can_return_memmap:
                    assert strip_length == l[-1][1] - l[-1][0], `strip_length, l[-1][1] - l[-1][0]`
                else:
                    strip_length = max (strip_length, l[-1][1] - l[-1][0])
                    strip_length_str = ' < ' + bytes2str(strip_length)
                if isinstance (bits_per_sample, numpy.ndarray):
                    assert (bits_per_sample == ifd.get_value('BitsPerSample', bits_per_sample)).all(),`bits_per_sample, ifd.get_value('BitsPerSample')`
                else:
                    assert (bits_per_sample == ifd.get_value('BitsPerSample', bits_per_sample)),`bits_per_sample, ifd.get_value('BitsPerSample')`
            if i>0:
                if i==1:
                    step = l[-1][0] - l[-2][1]
                    assert step>=0,`step, l[-2], l[-1]`
                else:
                    if step != l[-1][0] - l[-2][1]:
                        can_return_memmap = False
                        #assert step == l[-1][0] - l[-2][1],`step, l[-2], l[-1], (l[-1][0] - l[-2][1]), i`
            i += 1

        if verbose:
            bytes_per_image_str = bytes2str(bytes_per_image)
            print '''
width : %(width)s
length : %(length)s
depth : %(depth)s
sample_format : %(format)s
samples_per_pixel : %(samples_per_pixel)s
planar_config : %(planar_config)s
bits_per_sample : %(bits_per_sample)s
bits_per_pixel : %(bits_per_pixel)s

bytes_per_pixel : %(bytes_per_pixel)s
bytes_per_row : %(bytes_per_row)s
bytes_per_image : %(bytes_per_image_str)s

strips_per_image : %(strips_per_image)s
rows_per_strip : %(rows_per_strip)s
strip_length : %(strip_length_str)s
''' % (locals ())

        sample_names = ['sample%s' % (j) for j in range (samples_per_pixel)]
        depth = i

        if not can_return_memmap:
            if planar_config==1:
                if samples_per_pixel==1:
                    i = 0
                    arr = numpy.empty(depth * bytes_per_image, dtype=self.dtypes.uint8)
                    #bytes_per_strip = bytes_per_image // strips_per_image
                    bytes_per_strip = rows_per_strip * bytes_per_row
                    #assert len(l)==strips_per_image*depth,`len(l), strips_per_image, depth, bytes_per_strip`
                    for start, end in full_l:
                        #sys.stdout.write ("%s:%s," % (start, end)); sys.stdout.flush ()
                        if compression==1: # none
                            d = self.data[start:end]
                        elif compression==5: # lzw
                            d = self.data[start:end]
                            d = tif_lzw.decode(d, bytes_per_strip)
                        arr[i:i+d.nbytes] = d
                        i += d.nbytes
                    arr = arr.view(dtype=dtype_lst[0]).reshape((depth, length, width))
                    return [arr], sample_names
                else:
                    raise NotImplementedError(`samples_per_pixel`)
            else:
                raise NotImplementedError (`planar_config`)

        start = l[0][0]
        end = l[-1][1]
        if start > step:
            arr = self.data[start - step: end].reshape((depth, strip_length + step))
            k = step
        elif end <= self.data.size - step:
            arr = self.data[start: end+step].reshape((depth, strip_length + step))
            k = 0
        else:
            raise NotImplementedError (`start, end, step`)
        sys.stdout.flush()
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
                        tmp = arr[:,k:k+bytes]
                        #tmp = tmp.reshape((tmp.size,))
                        tmp = tmp.view(dtype=dtype_lst[j])
                        tmp = tmp.reshape((depth, length, width))
                        samples.append(tmp)
                        k += bytes
                else:
                    assert samples_per_pixel==1,`samples_per_pixel, bits_per_sample`
                    bytes = bits_per_sample // 8 * width * length
                    tmp = arr[:,k:k+bytes]
                    #tmp = tmp.reshape((tmp.size,))
                    tmp = tmp.view(dtype=dtype_lst[0])
                    tmp = tmp.reshape((depth, length, width))
                    samples.append(tmp)
                return samples, sample_names
            raise NotImplementedError (`planar_config, self.is_lsm`)
        elif planar_config==1:
            samples = []
            if isinstance(bits_per_sample, numpy.ndarray):
                bytes = sum(bits_per_sample[:samples_per_pixel]) // 8 * width * length
            else:
                bytes = bits_per_sample // 8 * width * length
            for j in range(samples_per_pixel):
                tmp = arr[:,k+j:k+j+bytes:samples_per_pixel]
                tmp = tmp.reshape((tmp.size,)).view(dtype=dtype_lst[j])
                tmp = tmp.reshape((depth, length, width))
                samples.append(tmp)
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

    def human (self):
        l = []
        for entry in self.entries:
            l.append(entry.human ())
        return '\n'.join(l)

    def get(self, tag_name):
        """Return IFD entry with given tag name.
        """
        for entry in self.entries:
            if entry.tag_name==tag_name:
                return entry
    def get_value(self, tag_name, default=None):
        """ Return the value of IFD entry with given tag name.

        When the entry does not exist, return default.
        """
        entry = self.get(tag_name)
        if entry is not None:
            return entry.value
        return default

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
                    dtype = getattr (self.dtypes, 'uint%s' % (bits_per_sample[i]))
                    r[channel_names[i]] = self.tiff.data[strip_offsets[i]:strip_offsets[i]+strip_nbytes[i]].view (dtype=dtype).reshape((width, length))
                else:
                    dtype = getattr (self.dtypes, 'uint%s' % (bits_per_sample))
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
        tag_name = self.tag_name = tag_value2name.get(self.tag,'TAG%s' % (hex(self.tag),))
        self.type_name = type2name.get(self.type, 'TYPE%s' % (self.type,))

        self.memory_usage = []
        if self.offset is not None:
            self.memory_usage.append((self.offset, self.offset + self.bytes*self.count, self.tag_name))

    @property
    def _value_str(self):
        tag_name = self.tag_name
        value = self.value
        if value is not None:
            if tag_name == 'ImageDescription':
                return ''.join(value.view('|S%s' % (value.nbytes//value.size)))
        return value

    def __str__(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance (r, str):
                return r
        if hasattr(self, 'value'):
            return 'IFDEntry(tag=%(tag_name)s, value=%(value)r, count=%(count)s, offset=%(offset)s)' % (self.__dict__)
        else:
            return 'IFDEntry(tag=%(tag_name)s, type=%(type_name)s, count=%(count)s, offset=%(offset)s)' % (self.__dict__)

    def human(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance (r, str):
                return r
        if hasattr(self, 'value'):
            self.value_str = self._value_str
            return 'IFDEntry(tag=%(tag_name)s, value=%(value_str)r, count=%(count)s, offset=%(offset)s)' % (self.__dict__)
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

# Register CZ LSM support:
lsm.register(locals())

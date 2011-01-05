""" Implements TIFF sample plane.
"""
# Author: Pearu Peterson
# Created: Jan 2011

from __future__ import division
import numpy
import tif_lzw

__all__ = ['TiffSamplePlane']

def set_array(output_array, input_array):
    dtype = numpy.uint8
    numpy.frombuffer(output_array.data, dtype=dtype)[:] = numpy.frombuffer(input_array.data, dtype=dtype)

class TiffSamplePlane:
    """ Image of a single sample in a TIFF image file directory.
    """

    def __init__(self, ifd, sample_index=0):
        """ Construct TiffSamplePlane instance.

        Parameters
        ----------
        ifd : `libtiff.tiff_file.IFDEntry`
        sample_index : int
          Specify sample index. When None then interpret pixel as a sample.
        """
        self.ifd = ifd
        self.sample_index = sample_index

        self.planar_config = planar_config = ifd.get_value('PlanarConfiguration')

        self.samples_per_pixel = samples_per_pixel = ifd.get_value('SamplesPerPixel')

        if sample_index is not None and sample_index >= samples_per_pixel:
            raise IndexError ('sample index %r must be less that nof samples %r' % (sample_index, samples_per_pixel))

        pixels_per_row = ifd.get_value('ImageWidth')
        rows_of_pixels = ifd.get_value('ImageLength')
        self.shape = (int(rows_of_pixels), int(pixels_per_row))

        rows_per_strip = ifd.get_value('RowsPerStrip')
        strips_per_image = (rows_of_pixels + rows_per_strip - 1) // rows_per_strip
        rows_per_strip = min(rows_of_pixels, rows_per_strip)
        self.rows_per_strip = rows_per_strip

        self.strip_offsets = strip_offsets = ifd.get_value('StripOffsets')
        self.strip_nbytes = strip_nbytes = ifd.get_value('StripByteCounts')
        self.sample_format = sample_format = ifd.get_value('SampleFormat')
        self.bits_per_sample = bits_per_sample = ifd.get_value('BitsPerSample')

        bits_per_pixel = sum(bits_per_sample)
        assert bits_per_pixel % 8==0, `bits_per_pixel, bits_per_sample`
        bytes_per_pixel = bits_per_pixel // 8
        
        if sample_index is None:
            bytes_per_sample = bytes_per_pixel
        else:
            bytes_per_sample = bits_per_sample[sample_index] // 8
        bytes_per_row = bytes_per_pixel * pixels_per_row
        bytes_per_strip = rows_per_strip * bytes_per_row

        sample_names = ifd.get_sample_names()
        pixel_dtype = ifd.get_pixel_dtype()

        sample_offset = 0
        if sample_index is None:
            dtype = pixel_dtype
            sample_names = ['pixel']
            sample_name = 'pixel'
        else:
            dtype = ifd.get_sample_dtypes ()[sample_index]
            sample_name = sample_names[sample_index]
            if planar_config==1:
                sample_offset = sum(bits_per_sample[:sample_index]) // 8

        bytes_per_row = pixels_per_row * bytes_per_pixel # uncompressed

        sample_offset = 0
        if planar_config==1 or sample_index is None:
            bytes_per_sample_row = bytes_per_row
        else:
            bytes_per_sample_row = bytes_per_row // samples_per_pixel

        self.dtype = dtype
        self.pixel_dtype = pixel_dtype

        self.bytes_per_pixel = bytes_per_pixel
        self.bytes_per_row = bytes_per_row
        self.bytes_per_sample_image = bytes_per_sample_row * rows_of_pixels
        self.uncompressed_bytes_per_strip = bytes_per_strip
        self.compression = compression = ifd.get_value('Compression')
        self.sample_name = sample_name
        self.sample_offset = sample_offset
        self.bytes_per_sample_row = bytes_per_sample_row
        self.strips_per_image = strips_per_image
        self.is_contiguous = compression==1 and ifd.is_contiguous()

        time = None
        descr = ifd.get_value('ImageDescription', human=True)
        if descr is not None:
            if descr.startswith ('<?xml') or descr[:4].lower()=='<ome':
                pass
            else:
                it = descr.find('RelativeTime')
                if it != -1:
                    time = float(descr[it:].split (None, 2)[1].strip())
        self.time = time

    def set_time (self, time):
        if None not in [self.time, time]:
            if self.time!=time:
                print '%s:warning: overwriting time value %s with %s' % (self.__class__.__name__, self.time, time)
        self.time = time

    def check_same_shape_and_type(self, other):
        return self.shape==other.shape and self.dtype==other.dtype

    def get_topology (self):
        return '''shape=%(shape)s planar_config=%(planar_config)s sample_index=%(sample_index)s
dtype=%(dtype)s pixel_dtype=%(pixel_dtype)s
bytes_per_pixel=%(bytes_per_pixel)s
bytes_per_sample_row=%(bytes_per_sample_row)s
bytes_per_row=%(bytes_per_row)s
bytes_per_strip=%(uncompressed_bytes_per_strip)s
bytes_per_sample_image=%(bytes_per_sample_image)s
strip_offsets=%(strip_offsets)s
strip_nbytes=%(strip_nbytes)s
strips_per_image=%(strips_per_image)s
rows_per_strip=%(rows_per_strip)s
''' % (self.__dict__)

    def get_row(self, index, subindex = None):
        if index < 0:
            index += self.shape[0]
        if index > self.shape[0] or index < 0:
            raise IndexError('Row index %r out of bounds [0,%r]' % (index, self.shape[0]-1))

        if self.planar_config==1: # RGBRGB..
            strip_index, row_index = divmod(index, self.rows_per_strip)
        else: # RR..GG..BB..
            index2 = self.sample_index * self.shape[0] + index
            strip_index, row_index = divmod(index2, self.rows_per_strip)

        start = self.strip_offsets[strip_index]
        stop = start +  self.strip_nbytes[strip_index]
        if self.compression==1:
            strip = self.ifd.tiff.data[start:stop]
        else:
            compressed_strip = self.ifd.tiff.data[start:stop]
            if self.compression==5: # lzw
                strip = tif_lzw.decode(compressed_strip, self.uncompressed_bytes_per_strip)
            else:
                raise NotImplementedError (`self.compression`)

        start = row_index * self.bytes_per_sample_row + self.sample_offset
        stop = start + self.bytes_per_sample_row + self.sample_offset

        if isinstance (subindex, tuple):
            if len(subindex)==1:
                subindex = subindex[0]

        if self.planar_config==1:
            if isinstance(subindex, (int, long)):
                start = start + subindex * self.bytes_per_pixel
                stop = start + self.bytes_per_pixel
                return strip[start:stop].view(dtype=self.pixel_dtype)[self.sample_name][0]
            row = strip[start:stop].view(dtype=self.pixel_dtype)[self.sample_name]
            if not row.size:
                print self.get_topology()
        else:
            row = strip[start:stop].view(dtype=self.dtype)
        if subindex is not None:
            return row[subindex]
        return row

    def get_rows(self, index, subindex=None):
        if isinstance(index, (int,long)):
            r = self.get_row (index, subindex=subindex)
            return r.reshape((1,)+r.shape)
        if isinstance (index, slice):
            indices = range (*index.indices(self.shape[0]))
            for i,j in enumerate(indices):
                s = self.get_row(j, subindex=subindex)
                if i==0:
                    r = numpy.empty((len (indices),)+s.shape, dtype=self.dtype)
                r[i] = s
            return r
        if isinstance (index, tuple):
            if len (index)==1:
                return self[index[0]]
        raise NotImplementedError (`index`)

    def get_image(self):
        if self.is_contiguous:
            if self.planar_config==1:
                start = self.strip_offsets[0] + self.sample_offset
                stop = self.strip_offsets[-1] + self.strip_nbytes[-1]
                image =self.ifd.tiff.data[start:stop].view(dtype=self.pixel_dtype)
                image = image[self.sample_name].reshape (self.shape)
                return image
            else:
                if self.sample_index is None:
                    start = self.strip_offsets[0]
                else:
                    start = self.strip_offsets[0] + self.sample_index * self.bytes_per_sample_image
                stop = start + self.bytes_per_sample_image
                image = self.ifd.tiff.data[start:stop]
                image = image.view(dtype=self.dtype).reshape(self.shape)
                return image
        else:
            image = numpy.empty((self.bytes_per_sample_image,), dtype=numpy.uint8)
            offset = 0
            for strip_index in range (len (self.strip_offsets)):
                start = self.strip_offsets[strip_index]
                stop = start +  self.strip_nbytes[strip_index]            
                if self.compression==1:
                    strip = self.ifd.tiff.data[start:stop]
                else:
                    compressed_strip = self.ifd.tiff.data[start:stop]
                    if self.compression==5: # lzw
                        strip = tif_lzw.decode(compressed_strip, self.uncompressed_bytes_per_strip)
                    else:
                        raise NotImplementedError (`self.compression`)
                image[offset:offset + strip.nbytes] = strip
                offset += strip.nbytes
            image = image.view(dtype=self.dtype).reshape(self.shape)
            return image

    def __len__(self):
        return self.shape[0]

    def __getitem__(self, index):
        if isinstance (index, (int, long)):
            return self.get_row(index)
        elif isinstance(index, slice):
            return self.get_image()[index]
        elif isinstance(index, tuple):
            if len(index)==0:
                return self.get_image()
            if len(index)==1:
                return self[index[0]]
            index0 = index[0]
            if isinstance(index0, (int, long)):
                return self.get_row(index0, index[1:])
            return self.get_image()[index]
        raise NotImplementedError (`index`)

class TiffSamplePlaneLazy(TiffSamplePlane):

    def __init__ (self, tiff_file_getter):
        self.tiff_file_getter = tiff_file_getter
        self.time = None
        self._ifd = None

    @property
    def ifd(self):
        ifd = self._ifd
        if ifd is None:
            tiff = self.tiff_file_getter()
            assert len (tiff.IFD)==1,`len (tiff.IFD)`
            self._ifd = ifd = tiff.IFD[0]
        return ifd

    @property
    def strip_offsets (self): return self.ifd.get_value ('StripOffsets')

    @property
    def strip_nbytes (self): return self.ifd.get_value ('StripByteCounts')

    @property
    def compression(self): return self.ifd.get_value ('Compression')

    @property
    def is_contiguous(self): return self.compression==1 and self.ifd.is_contiguous()

    def copy_attrs(self, other):
        for attr in ['sample_index', 'planar_config', 'samples_per_pixel','shape',
                     'rows_per_strip', 'sample_format', 'bits_per_sample',
                     'dtype', 'pixel_dtype', 'bytes_per_pixel', 'bytes_per_row',
                     'bytes_per_sample_image', 'uncompressed_bytes_per_strip',
                     'sample_name', 'sample_offset', 'bytes_per_sample_row',
                     'strips_per_image'
                     ]:
            setattr (self, attr, getattr (other, attr))

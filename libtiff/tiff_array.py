""" Implements an array of TIFF sample images.
"""
# Author: Pearu Peterson
# Created: Nov 2010

from __future__ import division

__all__ = ['TiffSamplePlane', 'TiffArray']

import numpy
import tif_lzw

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
            if self.is_contiguous or 1:
                return self.get_image()[index]
            return self.get_rows(index)
        elif isinstance(index, tuple):
            if len(index)==0:
                return self.get_image()
                if self.is_contiguous:
                    return self.get_image()
                return self.get_rows(slice(None))
            if len(index)==1:
                return self[index[0]]
            index0 = index[0]
            if isinstance(index0, (int, long)):
                return self.get_row(index0, index[1:])
            if self.is_contiguous:
                return self.get_image()[index]
            return self.get_rows(index0, index[1:])
        raise NotImplementedError (`index`)

class TiffArray:
    """ Holds a sequence of homogeneous TiffPlane's.

    TiffPlane's are homogeneous if they contain sample images of same
    shape and type. Otherwise TiffPlane's may contain images from
    different TIFF files with different pixel content.
    """
    def __init__ (self, planes):
        self.planes = []
        self.shape = ()
        self.dtype = None
        map(self.append, planes)

    def __len__(self):
        return self.shape[0]

    def __getitem__ (self, index):
        if isinstance(index, (int, long)):
            if self.sample_index is None:
                print self.shape
            return self.planes[index][()]
        elif isinstance (index, slice):
            indices = range (*index.indices(self.shape[0]))
            r = numpy.empty((len(indices),)+self.shape[1:], dtype=self.dtype)
            for i,j in enumerate(indices):
                r[i] = self.planes[j][()]
            return r
        elif isinstance(index, tuple):
            if len (index)==0:
                return self[:]
            if len (index)==1:
                return self[index[0]]
            index0 = index[0]
            if isinstance(index0, (int, long)):
                return self.planes[index0][index[1:]]
            elif isinstance (index0, slice):
                indices = range (*index0.indices(self.shape[0]))
                for i,j in enumerate(indices):
                    s = self.planes[j][index[1:]]
                    if i==0:
                        r = numpy.empty((len(indices),)+s.shape, dtype=self.dtype)
                    r[i] = s
                return r
        raise NotImplementedError (`index`)

    def append(self, plane):
        """ Append tiff plane to tiff array.
        """
        if self.planes:
            if not self.planes[0].check_same_shape_and_type (plane):
                raise TypeError('planes are not homogeneous (same shape and sample type), expected %s but got %s' % ((self.planes[0].shape, self.dtype), (plane.shape, plane.dtype)))
            self.shape = (self.shape[0]+1,) + self.shape[1:]
        else:
            self.dtype = plane.dtype
            self.shape = (1,) + plane.shape
            self.sample_index = plane.sample_index
        self.planes.append(plane)

    def extend(self, other):
        """ Extend tiff array with the content of another.
        """
        map(self.append, other.planes)
                
    def get_pixel_sizes(self):
        """ Return ZYX pixels sizes in microns.
        """
        ifd = self.planes[0].ifd
        if ifd.tiff.is_lsm:
            sample_spacing = ifd.tiff.lsminfo.get('recording sample spacing')[0]
            line_spacing = ifd.tiff.lsminfo.get('recording line spacing')[0]
            plane_spacing = ifd.tiff.lsminfo.get('recording plane spacing')[0]
            return (plane_spacing, line_spacing, sample_spacing)
        return (1,1,1)

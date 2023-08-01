"""
Provides TIFFimage class.
"""
# Author: Pearu Peterson
# Created: June 2010


import os
import sys
import time
import numpy
from . import tif_lzw

from .utils import bytes2str
from .tiff_data import tag_name2value, tag_value2type, tag_value2name, \
    name2type, type2bytes, type2dtype

VERBOSE = True


class TIFFentry:
    """ Hold a IFD entry used by TIFFimage.
    """

    def __init__(self, tag):
        if isinstance(tag, str):
            tag = tag_name2value[tag]
        assert isinstance(tag, int), repr(tag)
        self.tag = tag
        self.type_name = tag_value2type[tag]
        self.type = name2type[self.type_name]
        self.type_nbytes = type2bytes[self.type]
        self.type_dtype = type2dtype[self.type]
        self.tag_name = tag_value2name.get(self.tag,
                                           'TAG%s' % (hex(self.tag),))

        self.record = numpy.zeros((12,), dtype=numpy.ubyte)
        self.record[:2].view(dtype=numpy.uint16)[0] = self.tag
        self.record[2:4].view(dtype=numpy.uint16)[0] = self.type
        self.values = []

    def __str__(self):
        return '%s(entry=(%s,%s,%s,%s))' % (self.__class__.__name__,
                                            self.tag_name,
                                            self.type_name,
                                            self.count,
                                            self.offset)

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
    def offset_is_value(self):
        return not self.values and self.count[0] == 1 and \
            self.type_nbytes <= 4 and self.type_name != 'ASCII'

    def __getitem__(self, index):
        if self.offset_is_value:
            if index > 0:
                raise IndexError(repr(index))
            return self.offset[0]
        return self.values[index]

    def add_value(self, value):
        if isinstance(value, (list, tuple)):
            list(map(self.add_value, value))
        elif self.type_name == 'ASCII':
            value = str(value)
            if self.count[0] == 0:
                self.values.append(value)
            else:
                self.values[0] += value
            self.count[0] = len(self.values[0]) + 1
        elif self.type_nbytes <= 4:
            self.count[0] += 1
            if self.count[0] == 1:
                self.offset[0] = value
            elif self.count[0] == 2:
                self.values.append(self.offset[0])
                self.values.append(value)
                self.offset[0] = 0
            else:
                self.values.append(value)
        else:
            self.count[0] += 1
            self.values.append(value)

    def set_value(self, value):
        assert self.type_name != 'ASCII', repr(self)
        if self.count[0]:
            self.count[0] -= 1
            if self.values:
                del self.values[-1]
        self.add_value(value)

    def set_offset(self, offset):
        self.offset[0] = offset

    def toarray(self, target=None):
        if self.offset_is_value:
            return
        if target is None:
            target = numpy.zeros((self.nbytes,), dtype=numpy.ubyte)
        dtype = target.dtype
        offset = 0
        # print(self.values)
        # print(dtype)
        if self.type_name == 'ASCII':
            data = numpy.array([self.values[0] + '\0'])
            # print(type(data), data)
            data = numpy.array([self.values[0] + '\0'],
                               dtype='|S{}'.format(len(self.values[0]) + 1)).view(dtype=numpy.ubyte)
            # print(type(data), data)
            target[offset:offset + self.nbytes] = data
        else:
            for value in self.values:
                dtype = self.type_dtype
                if self.type_name == 'RATIONAL' and isinstance(value,
                                                               (int, float)):
                    dtype = numpy.float64
                target[offset:offset + self.type_nbytes].view(dtype=dtype)[
                    0] = value
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
        # dtype = None
        if isinstance(data, list):
            image = data[0]
            self.length, self.width = image.shape
            self.depth = len(data)
            dtype = image.dtype
        elif isinstance(data, numpy.ndarray):
            shape = data.shape
            dtype = data.dtype
            if len(shape) == 1:
                self.width, = shape
                self.length = 1
                self.depth = 1
                data = [[data]]
            elif len(shape) == 2:
                self.length, self.width = shape
                self.depth = 1
                data = [data]
            elif len(shape) == 3:
                self.depth, self.length, self.width = shape
            else:
                raise NotImplementedError(repr(shape))
        else:
            raise NotImplementedError(repr(type(data)))
        self.data = data
        self.dtype = dtype
        self.description = description

    # noinspection PyProtectedMember
    def write_file(self, filename, compression='none',
                   strip_size=2 ** 13, planar_config=1,
                   validate=False, verbose=None):
        """
        Write image data to TIFF file.

        Parameters
        ----------
        filename : str
        compression : {'none', 'lzw'}
        strip_size : int
          Specify the size of uncompressed strip.
        planar_config : int
        validate : bool
          When True then check compression by decompression.
        verbose : {bool, None}
          When True then write progress information to stdout. When None
          then verbose is assumed for data that has size over 1MB.

        Returns
        -------
        compression : float
          Compression factor.
        """
        if verbose is None:
            nbytes = self.depth * self.length * self.width * \
                self.dtype.itemsize
            verbose = nbytes >= 1024 ** 2

        if os.path.splitext(filename)[1].lower() not in ['.tif', '.tiff']:
            filename += '.tif'

        if verbose:
            sys.stdout.write('Writing TIFF records to %s\n' % filename)
            sys.stdout.flush()

        compression_map = dict(packbits=32773, none=1, lzw=5, jpeg=6,
                               ccitt1d=2,
                               group3fax=3, group4fax=4
                               )
        compress_map = dict(none=lambda _data: _data,
                            lzw=tif_lzw.encode)
        decompress_map = dict(none=lambda _data, _bytes: _data,
                              lzw=tif_lzw.decode)
        compress = compress_map.get(compression or 'none', None)
        if compress is None:
            raise NotImplementedError(repr(compression))
        decompress = decompress_map.get(compression or 'none', None)
        # compute tif file size and create image file directories data
        image_directories = []
        total_size = 8
        data_size = 0
        image_data_size = 0
        for i, image in enumerate(self.data):
            if verbose:
                sys.stdout.write('\r  creating records: %5s%% done  ' % (
                    int(100.0 * i / len(self.data))))
                sys.stdout.flush()
            if image.dtype.kind == 'V' and len(
                    image.dtype.names) == 3:  # RGB image
                sample_format = dict(u=1, i=2, f=3, c=6).get(
                    image.dtype.fields[image.dtype.names[0]][0].kind)
                bits_per_sample = [image.dtype.fields[f][0].itemsize * 8 for f
                                   in image.dtype.names]
                samples_per_pixel = 3
                photometric_interpretation = 2
            else:  # gray scale image
                sample_format = dict(u=1, i=2, f=3, c=6).get(image.dtype.kind)
                bits_per_sample = image.dtype.itemsize * 8
                samples_per_pixel = 1
                photometric_interpretation = 1
            if sample_format is None:
                print('Warning(TIFFimage.write_file): unknown data kind %r, '
                      'mapping to void' % image.dtype.kind)
                sample_format = 4
            length, width = image.shape
            bytes_per_row = width * image.dtype.itemsize
            rows_per_strip = min(length,
                                 int(numpy.ceil(
                                     float(strip_size) / bytes_per_row)))
            strips_per_image = int(
                numpy.floor(float(
                    length + rows_per_strip - 1) / rows_per_strip))
            assert bytes_per_row * rows_per_strip * \
                strips_per_image >= image.nbytes
            d = dict(ImageWidth=width,
                     ImageLength=length,
                     Compression=compression_map.get(compression, 1),
                     PhotometricInterpretation=photometric_interpretation,
                     PlanarConfiguration=planar_config,
                     Orientation=1,
                     ResolutionUnit=1,
                     XResolution=1,
                     YResolution=1,
                     SamplesPerPixel=samples_per_pixel,
                     RowsPerStrip=rows_per_strip,
                     BitsPerSample=bits_per_sample,
                     SampleFormat=sample_format,
                     )
            if i == 0:
                d.update(dict(
                    ImageDescription=self.description,
                    Software='http://code.google.com/p/pylibtiff/'))

            entries = []
            for tagname, value in list(d.items()):
                entry = TIFFentry(tagname)
                entry.add_value(value)
                entries.append(entry)
                total_size += 12 + entry.nbytes
                data_size += entry.nbytes

            strip_byte_counts = TIFFentry('StripByteCounts')
            strip_offsets = TIFFentry('StripOffsets')
            entries.append(strip_byte_counts)
            entries.append(strip_offsets)
            # strip_offsets and strip_byte_counts will be filled in the next
            # loop
            if strips_per_image == 1:
                assert strip_byte_counts.type_nbytes <= 4
                assert strip_offsets.type_nbytes <= 4
                total_size += 2 * 12
            else:
                total_size += 2 * 12 + strips_per_image * (
                    strip_byte_counts.type_nbytes + strip_offsets.type_nbytes)
                data_size += strips_per_image * (
                    strip_byte_counts.type_nbytes + strip_offsets.type_nbytes)

            # image data:
            total_size += image.nbytes
            data_size += image.nbytes
            image_data_size += image.nbytes

            # records for nof IFD entries and offset to the next IFD:
            total_size += 2 + 4

            # entries must be sorted by tag number
            entries.sort(key=lambda x: x.tag)

            strip_info = strip_offsets, strip_byte_counts, strips_per_image, \
                rows_per_strip, bytes_per_row
            image_directories.append((entries, strip_info, image))

        tif = numpy.memmap(filename, dtype=numpy.ubyte, mode='w+',
                           shape=(total_size,))

        # noinspection PyProtectedMember
        def tif_write(_tif, _offset, _data):
            end = _offset + _data.nbytes
            if end > _tif.size:
                size_incr = int(
                    float(end - _tif.size) / 1024 ** 2 + 1) * 1024 ** 2
                new_size = _tif.size + size_incr
                assert end <= new_size, repr(
                    (end, _tif.size, size_incr, new_size))
                # sys.stdout.write('resizing: %s -> %s\n' % (tif.size,
                # new_size))
                # tif.resize(end, refcheck=False)
                _base = _tif._mmap
                if _base is None:
                    _base = _tif.base
                _base.resize(new_size)
                new_tif = numpy.ndarray.__new__(numpy.memmap, (_base.size(),),
                                                dtype=_tif.dtype, buffer=_base)
                new_tif._parent = _tif
                new_tif.__array_finalize__(_tif)
                _tif = new_tif
            _tif[_offset:end] = _data
            return _tif

        # write TIFF header
        tif[:2].view(dtype=numpy.uint16)[0] = 0x4949  # low-endian
        tif[2:4].view(dtype=numpy.uint16)[0] = 42  # magic number
        tif[4:8].view(dtype=numpy.uint32)[0] = 8  # offset to the first IFD

        offset = 8
        data_offset = total_size - data_size
        image_data_offset = total_size - image_data_size
        first_data_offset = data_offset
        first_image_data_offset = image_data_offset
        start_time = time.time()
        compressed_data_size = 0
        for i, (entries, strip_info, image) in enumerate(image_directories):
            strip_offsets, strip_byte_counts, strips_per_image, \
                rows_per_strip, bytes_per_row = strip_info

            # write the nof IFD entries
            tif[offset:offset + 2].view(dtype=numpy.uint16)[0] = len(entries)
            offset += 2
            assert offset <= first_data_offset, repr(
                (offset, first_data_offset))

            # write image data
            data = image.view(dtype=numpy.ubyte).reshape((image.nbytes,))

            for j in range(strips_per_image):
                c = rows_per_strip * bytes_per_row
                k = j * c
                c -= max((j + 1) * c - image.nbytes, 0)
                assert c > 0, repr(c)
                orig_strip = data[k:k + c]  # type: numpy.ndarray

                strip = compress(orig_strip)
                if validate:
                    test_strip = decompress(strip, orig_strip.nbytes)
                    if (orig_strip != test_strip).any():
                        raise RuntimeError(
                            'Compressed data is corrupted: cannot recover '
                            'original data')
                compressed_data_size += strip.nbytes
                # print strip.size, strip.nbytes, strip.shape,
                # tif[image_data_offset:image_data_offset+strip.nbytes].shape
                strip_offsets.add_value(image_data_offset)
                strip_byte_counts.add_value(strip.nbytes)

                tif = tif_write(tif, image_data_offset, strip)
                image_data_offset += strip.nbytes
                # if j == 0:
                #     first = strip_offsets[0]
                # last = strip_offsets[-1] + strip_byte_counts[-1]

            # write IFD entries
            for entry in entries:
                data_size = entry.nbytes
                if data_size:
                    entry.set_offset(data_offset)
                    assert data_offset + data_size <= total_size, repr(
                        (data_offset + data_size, total_size))
                    r = entry.toarray(tif[data_offset:data_offset + data_size])
                    assert r.nbytes == data_size
                    data_offset += data_size
                    assert data_offset <= first_image_data_offset, repr(
                        (data_offset, first_image_data_offset, i))
                tif[offset:offset + 12] = entry.record
                offset += 12
                assert offset <= first_data_offset, repr(
                    (offset, first_data_offset, i))

            # write offset to the next IFD
            tif[offset:offset + 4].view(dtype=numpy.uint32)[0] = offset + 4
            offset += 4
            assert offset <= first_data_offset, repr(
                (offset, first_data_offset))

            if verbose:
                sys.stdout.write(
                    '\r  filling records: %5s%% done (%s/s)%s' %
                    (int(100.0 * (i + 1) / len(image_directories)),
                     bytes2str(int(float(image_data_offset - first_image_data_offset) / (time.time() - start_time))),
                     ' ' * 2))
                if (i + 1) == len(image_directories):
                    sys.stdout.write('\n')
                sys.stdout.flush()

        # last offset must be 0
        tif[offset - 4:offset].view(dtype=numpy.uint32)[0] = 0

        compression = 1 / (float(compressed_data_size) / image_data_size)

        if compressed_data_size != image_data_size:
            sdiff = image_data_size - compressed_data_size
            total_size -= sdiff
            base = tif._mmap
            if base is None:
                base = tif.base
            base.resize(total_size)
            if verbose:
                sys.stdout.write(
                    '  resized records: %s -> %s (compression: %.2fx)\n'
                    % (bytes2str(total_size + sdiff), bytes2str(total_size),
                       compression))
                sys.stdout.flush()
        del tif  # flushing
        return compression

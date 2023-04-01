"""
Provides TIFFfile class.
"""
# Author: Pearu Peterson
# Created: June 2010


__all__ = ['TIFFfile', 'TiffFile']

import os
import sys
import shutil
import warnings
import numpy
import mmap
from .tiff_data import type2name, name2type, type2bytes, tag_value2name
from .tiff_data import LittleEndianNumpyDTypes, BigEndianNumpyDTypes, \
    default_tag_values, sample_format_map
from .utils import bytes2str, isindisk
from .tiff_base import TiffBase
from .tiff_sample_plane import TiffSamplePlane
from .tiff_array import TiffArray

from . import lsm
from . import tif_lzw

IFDEntry_init_hooks = []
IFDEntry_finalize_hooks = []

IOError_too_many_open_files_hint = '''%s
======================================================================
Ubuntu Linux users:
  Check `ulimit -n`.
  To increase the number of open files limits, add the following lines
    *            hard    nofile          16384
    *            soft    nofile          16384
  to /etc/security/limits.conf and run `sudo start procps`
======================================================================
'''

OSError_operation_not_permitted_hint = '''%s
======================================================================
The exception may be due to unsufficient access rights or due to
opening too many files for the given file system (NFS, for instance).
======================================================================
'''


class TIFFfile(TiffBase):
    """
    Hold a TIFF file image stack that is accessed via memmap.
    To access image, use get_tiff_array method.

    Attributes
    ----------
    filename : str
    data : memmap (or array when use_memmap is False)
    IFD : IFD-list

    See also
    --------
    TiffFiles, TiffChannelsAndFiles
    """

    def close(self):
        if hasattr(self, 'data'):
            if self.verbose:
                sys.stdout.write('Closing TIFF file %r\n' % (self.filename))
                sys.stdout.flush()
            for ifd in self.IFD:
                ifd.close()
            if self.use_memmap:
                # newer numpy does not have memmap.close anymore [May 2012]
                # self.data.base.close()
                pass
            del self.data

    __del__ = close

    def __init__(self, filename, mode='r', first_byte=0, verbose=False,
                 local_cache=None, use_memmap=True):
        """
        local_cache : {None, str}
          Specify path to local cache. Local cache will be used to
          temporarily store files from external devises such as NFS.
        """

        self.verbose = verbose
        self.first_byte = first_byte
        self.use_memmap = use_memmap
        try:
            if local_cache is not None:
                cache_filename = local_cache + '/' + filename
                if os.path.exists(cache_filename):
                    filename = cache_filename
                elif not isindisk(filename):
                    assert isindisk(local_cache), repr(local_cache)
                    dirname = os.path.dirname(cache_filename)
                    if not os.path.isdir(dirname):
                        os.makedirs(dirname)
                    shutil.copyfile(filename, cache_filename)
                    filename = cache_filename
            if verbose:
                sys.stdout.write('Opening file %r\n' % (filename))
                sys.stdout.flush()
            if mode != 'r':
                raise NotImplementedError(repr(mode))
            if not os.path.isfile(filename):
                raise ValueError('file does not exists')
            if not os.stat(filename).st_size:
                raise ValueError('file has zero size')
            if use_memmap:
                self.data = numpy.memmap(filename, dtype=numpy.ubyte,
                                         mode=mode)
            else:
                assert mode == 'r', repr(mode)
                f = open(filename, 'rb')
                self.data = numpy.frombuffer(f.read(), dtype=numpy.ubyte)
                f.close()
        except IOError as msg:
            if 'Too many open files' in str(msg):
                raise IOError(IOError_too_many_open_files_hint % msg)
            if 'Operation not permitted' in str(msg):
                raise IOError(OSError_operation_not_permitted_hint % msg)
            raise
        except OSError as msg:
            if 'Operation not permitted' in str(msg):
                raise OSError(OSError_operation_not_permitted_hint % msg)
            raise
        except mmap.error as msg:
            if 'Too many open files' in str(msg):
                raise mmap.error(IOError_too_many_open_files_hint % msg)
            raise

        self.filename = filename

        self.memory_usage = [(self.data.nbytes, self.data.nbytes, 'eof')]

        byteorder = self.data[first_byte:first_byte + 2].view(
            dtype=numpy.uint16)[0]

        if byteorder == 0x4949:
            self.endian = 'little'
            self.dtypes = LittleEndianNumpyDTypes
        elif byteorder == 0x4d4d:
            self.endian = 'big'
            self.dtypes = BigEndianNumpyDTypes
        else:
            raise ValueError('unrecognized byteorder: %s' % (hex(byteorder)))
        magic = self.get_uint16(first_byte + 2)
        if magic != 42:
            raise ValueError('wrong magic number for TIFF file: %s' % (magic))
        self.IFD0 = IFD0 = first_byte + self.get_uint32(first_byte + 4)

        self.memory_usage.append((first_byte, first_byte + 8, 'file header'))

        n = self.get_uint16(IFD0)
        IFD_list = []
        IFD_offset = IFD0
        while IFD_offset:
            n = self.get_uint16(IFD_offset)
            ifd = IFD(self)
            exif_offset = 0
            for i in range(n):
                entry = IFDEntry(ifd, self, IFD_offset + 2 + i * 12)
                ifd.append(entry)
                if entry.tag == 0x8769:  # TIFFTAG_EXIFIFD
                    exif_offset = entry.value
            ifd.finalize()
            IFD_list.append(ifd)
            self.memory_usage.append((IFD_offset, IFD_offset + 2 + n * 12 + 4,
                                      'IFD%s entries(%s)' % (
                                          len(IFD_list), len(ifd))))
            IFD_offset = self.get_uint32(IFD_offset + 2 + n * 12)
            if IFD_offset == 0 and exif_offset != 0:
                IFD_offset = exif_offset
                exif_offset = 0
            if verbose:
                sys.stdout.write(
                    '\rIFD information read: %s..' % (len(IFD_list)))
                sys.stdout.flush()

        self.IFD = IFD_list
        if verbose:
            sys.stdout.write(' done\n')
            sys.stdout.flush()

        self.time = None

    def set_time(self, time):
        self.time = time

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.filename)

    def get_uint16(self, offset):
        return self.data[offset:offset + 2].view(dtype=self.dtypes.uint16)[0]

    def get_uint32(self, offset):
        return self.data[offset:offset + 4].view(dtype=self.dtypes.uint32)[0]

    def get_int16(self, offset):
        return self.data[offset:offset + 2].view(dtype=self.dtypes.int16)[0]

    def get_int32(self, offset):
        return self.data[offset:offset + 4].view(dtype=self.dtypes.int32)[0]

    def get_float32(self, offset):
        return self.data[offset:offset + 4].view(dtype=self.dtypes.float32)[0]

    def get_float64(self, offset):
        return self.data[offset:offset + 8].view(dtype=self.dtypes.float64)[0]

    get_short = get_uint16
    get_long = get_uint32
    get_double = get_float64

    def get_value(self, offset, typ):
        values = self.get_values(offset, typ, 1)
        if values is not None:
            return values[0]

    def get_values(self, offset, typ, count):
        if isinstance(typ, numpy.dtype):
            dtype = typ
            bytes = typ.itemsize
        elif isinstance(typ, type) and issubclass(typ, numpy.generic):
            dtype = typ
            bytes = typ().itemsize
        else:
            if isinstance(typ, str):
                ntyp = typ
                typ = name2type.get(typ)
            else:
                ntyp = str(typ)
            dtype = self.dtypes.type2dt.get(typ)
            bytes = type2bytes.get(typ)
            if dtype is None or bytes is None:
                warnings.warn('incomplete info for type=%r [%r]: dtype=%s, bytes=%s\n' % (
                    typ, ntyp, dtype, bytes), stacklevel=2)
                return
        return self.data[offset:offset + bytes * count].view(dtype=dtype)

    def get_string(self, offset, length=None):
        if length is None:
            i = 0
            while self.data[offset + i]:
                i += 1
            length = i
        string = self.get_values(offset, 'BYTE', length).tostring()
        return string

    def check_memory_usage(self, verbose=True):
        '''Check memory usage of TIFF fields and blocks.

        Returns
        -------
        ok : bool

          Return False if unknown or overlapping memory areas have
          been detected.

        '''
        lst = []
        lst.extend(self.memory_usage)
        for ifd in self.IFD:
            lst.extend(ifd.memory_usage)
        lst.sort()
        last_end = None
        ok = True
        for start, end, resource in lst:
            if last_end:
                if last_end != start:
                    if verbose:
                        print('--- unknown %s bytes' % (start - last_end))
                    ok = False
                    if start < last_end and verbose:
                        print('--- overlapping memory area')
            if verbose:
                print('%s..%s[%s] contains %s' % (
                    start, end, end - start, resource))
            last_end = end
        return ok

    def is_contiguous(self):
        end = None
        for i, ifd in enumerate(self.IFD):
            strip_offsets = ifd.get('StripOffsets').value
            strip_nbytes = ifd.get('StripByteCounts').value
            if not ifd.is_contiguous():
                return False
            if i == 0:
                pass
            else:
                if isinstance(strip_offsets, numpy.ndarray):
                    start = strip_offsets[0]
                else:
                    start = strip_offsets
                if end != start:
                    return False
            if isinstance(strip_offsets, numpy.ndarray):
                end = strip_offsets[-1] + strip_nbytes[-1]
            else:
                end = strip_offsets + strip_nbytes
        return True

    def get_contiguous(self):
        """ Return memmap of a stack of images.
        """
        if not self.is_contiguous():
            raise ValueError('Image stack data not contiguous')
        ifd0 = self.IFD[0]
        ifd1 = self.IFD[-1]
        width = ifd0.get('ImageWidth').value
        length = ifd0.get('ImageLength').value
        assert width == ifd1.get('ImageWidth').value
        assert length == ifd1.get('ImageLength').value
        depth = len(self.IFD)
        compression = ifd0.get('Compression').value
        if compression != 1:
            raise ValueError(
                'Unable to get contiguous image stack from compressed data')
        bits_per_sample = ifd0.get('BitsPerSample').value
        # photo_interp = ifd0.get('PhotometricInterpretation').value
        # planar_config = ifd0.get('PlanarConfiguration').value
        strip_offsets0 = ifd0.get('StripOffsets').value
        # strip_nbytes0 = ifd0.get('StripByteCounts').value
        strip_offsets1 = ifd1.get('StripOffsets').value
        strip_nbytes1 = ifd1.get('StripByteCounts').value
        samples_per_pixel = ifd1.get('SamplesPerPixel').value
        assert samples_per_pixel == 1, repr(samples_per_pixel)

        if isinstance(bits_per_sample, numpy.ndarray):
            dtype = getattr(self.dtypes, 'uint%s' % (bits_per_sample[0]))
        else:
            dtype = getattr(self.dtypes, 'uint%s' % (bits_per_sample))

        if isinstance(strip_offsets0, numpy.ndarray):
            start = strip_offsets0[0]
            end = strip_offsets1[-1] + strip_nbytes1[-1]
        else:
            start = strip_offsets0
            end = strip_offsets1 + strip_nbytes1
        return self.data[start:end].view(dtype=dtype).reshape(
            (depth, width, length))

    def get_subfile_types(self):
        """ Return a list of subfile types.
        """
        s = set()
        for ifd in self.IFD:
            s.add(ifd.get_value('NewSubfileType'))
        return sorted(s)

    def get_depth(self, subfile_type=0):
        depth = 0
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType') == subfile_type:
                depth += 1
        return depth

    def get_first_ifd(self, subfile_type=0):
        """Return the first IFD entry with given subfile type.

        Parameters
        ----------
        subfile_type : {0, 1, 2, 4}

          Specify subfile type. 0: image, 1: reduced image, 2: single
          page, 4: transparency mask.

        Returns
        -------
        ifd : IFDEntry

        """
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType') == subfile_type:
                return ifd

    def get_tiff_array(self, sample_index=0, subfile_type=0):
        """ Create array of sample images.

        Parameters
        ----------
        sample_index : int
          Specify sample within a pixel.
        subfile_type : int
          Specify TIFF NewSubfileType used for collecting sample images.

        Returns
        -------
        tiff_array : TiffArray
          Array of sample images. The array has rank equal to 3.
        """
        planes = []
        index = 0
        time_lst = self.time
        for ifd in self.IFD:
            if ifd.get_value('NewSubfileType', subfile_type) != subfile_type:
                # subfile_type: 0: image, 1: reduced image,
                # 2: single page, 4: transparency mask
                continue
            plane = TiffSamplePlane(ifd, sample_index=sample_index)
            if time_lst is not None:
                plane.set_time(time_lst[index])
            planes.append(plane)
            index += 1
        tiff_array = TiffArray(planes)
        return tiff_array

    def get_samples(self, subfile_type=0, verbose=False):
        """Return samples and sample names.

        Parameters
        ----------
        subfile_type : {0, 1}
          Specify subfile type. Subfile type 1 corresponds to reduced
          resolution image.
        verbose : bool
          When True the print out information about samples

        Returns
        -------
        samples : list
          List of numpy.memmap arrays of samples
        sample_names : list
          List of the corresponding sample names

        """
        lst = []
        i = 0
        step = 0
        can_return_memmap = True
        ifd_lst = [ifd for ifd in self.IFD if
                   ifd.get_value('NewSubfileType') == subfile_type]

        depth = len(ifd_lst)
        full_l = []
        for ifd in ifd_lst:
            if not ifd.is_contiguous():
                raise NotImplementedError('none contiguous strips')

            strip_offsets = ifd.get_value('StripOffsets')
            strip_nbytes = ifd.get_value('StripByteCounts')
            lst.append(
                (strip_offsets[0], strip_offsets[-1] + strip_nbytes[-1]))
            for off, nb in zip(strip_offsets, strip_nbytes):
                full_l.append((off, off + nb))

            if i == 0:
                compression = ifd.get_value('Compression')
                if compression != 1:
                    can_return_memmap = False
                width = ifd.get_value('ImageWidth')
                length = ifd.get_value('ImageLength')
                samples_per_pixel = ifd.get_value('SamplesPerPixel')
                planar_config = ifd.get_value('PlanarConfiguration')
                bits_per_sample = ifd.get_value('BitsPerSample')
                sample_format = ifd.get_value('SampleFormat')[0]
                photometric_interpretation = ifd.get_value(
                    'PhotometricInterpretation')
                if self.is_lsm or not isinstance(strip_offsets, numpy.ndarray):
                    strips_per_image = 1
                else:
                    strips_per_image = len(strip_offsets)
                format = sample_format_map.get(sample_format)
                if format is None:
                    print(
                        'Warning(TIFFfile.get_samples): unsupported'
                        ' sample_format=%s is mapped to uint' % (
                            sample_format))
                    format = 'uint'

                dtype_lst = []
                bits_per_pixel = 0
                for j in range(samples_per_pixel):
                    bits = bits_per_sample[j]
                    bits_per_pixel += bits
                    dtype = getattr(self.dtypes, '%s%s' % (format, bits))
                    dtype_lst.append(dtype)
                bytes_per_pixel = bits_per_pixel // 8
                assert 8 * bytes_per_pixel == bits_per_pixel, repr(
                    bits_per_pixel)
                bytes_per_row = width * bytes_per_pixel
                strip_length = lst[-1][1] - lst[-1][0]
                strip_length_str = bytes2str(strip_length)
                bytes_per_image = length * bytes_per_row

                rows_per_strip = bytes_per_image // (
                    bytes_per_row * strips_per_image)
                if bytes_per_image % (bytes_per_row * strips_per_image):
                    rows_per_strip += 1
                assert rows_per_strip == ifd.get_value('RowsPerStrip',
                                                       rows_per_strip), \
                    repr((rows_per_strip,
                          ifd.get_value('RowsPerStrip'),
                          bytes_per_image,
                          bytes_per_row,
                          strips_per_image,
                          self.filename))
            else:
                assert width == ifd.get_value('ImageWidth', width), repr(
                    (width, ifd.get_value('ImageWidth')))
                assert length == ifd.get_value('ImageLength', length), repr(
                    (length, ifd.get_value('ImageLength')))
                # assert samples_per_pixel == ifd.get(
                # 'SamplesPerPixel').value, `samples_per_pixel, ifd.get(
                # 'SamplesPerPixel').value`
                assert planar_config == ifd.get_value('PlanarConfiguration',
                                                      planar_config)
                if can_return_memmap:
                    assert strip_length == lst[-1][1] - lst[-1][0], repr(
                        (strip_length, lst[-1][1] - lst[-1][0]))
                else:
                    strip_length = max(strip_length, lst[-1][1] - lst[-1][0])
                    strip_length_str = ' < ' + bytes2str(strip_length)

                assert (bits_per_sample == ifd.get_value(
                    'BitsPerSample',
                    bits_per_sample)).all(), repr(
                        (bits_per_sample, ifd.get_value('BitsPerSample')))
            if i > 0:
                if i == 1:
                    step = lst[-1][0] - lst[-2][1]
                    assert step >= 0, repr((step, lst[-2], lst[-1]))
                else:
                    if step != lst[-1][0] - lst[-2][1]:
                        can_return_memmap = False
            i += 1

        if verbose:
            bytes_per_image_str = bytes2str(bytes_per_image)
            print('''
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
''' % (locals()))

        if photometric_interpretation == 2:
            assert samples_per_pixel == 3, repr(samples_per_pixel)
            sample_names = ['red', 'green', 'blue']
        else:
            sample_names = ['sample%s' % (j) for j in range(samples_per_pixel)]
        depth = i

        if not can_return_memmap:
            if planar_config == 1:
                if samples_per_pixel == 1:
                    i = 0
                    arr = numpy.empty(depth * bytes_per_image,
                                      dtype=self.dtypes.uint8)
                    bytes_per_strip = rows_per_strip * bytes_per_row
                    for start, end in full_l:
                        if compression == 1:  # none
                            d = self.data[start:end]
                        elif compression == 5:  # lzw
                            d = self.data[start:end]
                            d = tif_lzw.decode(d, bytes_per_strip)
                        arr[i:i + d.nbytes] = d
                        i += d.nbytes
                    arr = arr.view(dtype=dtype_lst[0]).reshape(
                        (depth, length, width))
                    return [arr], sample_names
                else:
                    i = 0
                    arr = numpy.empty(depth * bytes_per_image,
                                      dtype=self.dtypes.uint8)
                    bytes_per_strip = rows_per_strip * bytes_per_row
                    for start, end in full_l:
                        sys.stdout.write("%s:%s," % (start, end))
                        sys.stdout.flush()
                        if compression == 1:  # none
                            d = self.data[start:end]
                        elif compression == 5:  # lzw
                            d = self.data[start:end]
                            d = tif_lzw.decode(d, bytes_per_strip)
                        arr[i:i + d.nbytes] = d
                        i += d.nbytes
                    dt = numpy.dtype(
                        dict(names=sample_names, formats=dtype_lst))
                    arr = arr.view(dtype=dt).reshape((depth, length, width))
                    return [arr[n] for n in arr.dtype.names], arr.dtype.names
                    raise NotImplementedError(
                        repr((depth, bytes_per_image, samples_per_pixel)))
            else:
                raise NotImplementedError(repr(planar_config))

        start = lst[0][0]
        end = lst[-1][1]
        if start > step:
            arr = self.data[start - step: end].reshape(
                (depth, strip_length + step))
            k = step
        elif end <= self.data.size - step:
            arr = self.data[start: end + step].reshape(
                (depth, strip_length + step))
            k = 0
        else:
            raise NotImplementedError(repr((start, end, step)))
        sys.stdout.flush()
        if planar_config == 2:
            if self.is_lsm:
                # LSM510: one strip per image plane channel
                if subfile_type == 0:
                    sample_names = self.lsminfo.get('data channel name')
                elif subfile_type == 1:
                    sample_names = ['red', 'green', 'blue']
                    assert samples_per_pixel == 3, repr(samples_per_pixel)
                else:
                    raise NotImplementedError(repr(subfile_type))
                samples = []

                for j in range(samples_per_pixel):
                    bytes = bits_per_sample[j] // 8 * width * length
                    tmp = arr[:, k:k + bytes]
                    tmp = tmp.view(dtype=dtype_lst[j])
                    tmp = tmp.reshape((depth, length, width))
                    samples.append(tmp)
                    k += bytes
                return samples, sample_names
            raise NotImplementedError(repr((planar_config, self.is_lsm)))
        elif planar_config == 1:
            samples = []
            bytes = sum(
                bits_per_sample[:samples_per_pixel]) // 8 * width * length
            bytes_per_sample = bits_per_sample // 8
            for j in range(samples_per_pixel):
                i0 = k + j * bytes_per_sample[j]
                # print j, i0, i0+bytes, samples_per_pixel, arr.shape
                tmp = arr[:, i0:i0 + bytes:samples_per_pixel]
                tmp = numpy.array(tmp.reshape((tmp.size,)))
                tmp = tmp.view(dtype=dtype_lst[j])
                tmp = tmp.reshape((depth, length, width))
                samples.append(tmp)
                # k += bytes
            return samples, sample_names
        else:
            raise NotImplementedError(repr(planar_config))

    def get_info(self):
        """ Return basic information about the file.
        """
        lst = []
        subfile_types = self.get_subfile_types()
        lst.append('Number of subfile types: %s' % (len(subfile_types)))
        for subfile_type in subfile_types:
            ifd = self.get_first_ifd(subfile_type=subfile_type)
            lst.append('-' * 50)
            lst.append('Subfile type: %s' % (subfile_type))
            lst.append('Number of images: %s' % (
                self.get_depth(subfile_type=subfile_type)))
            for tag in ['ImageLength',
                        'ImageWidth',
                        'SamplesPerPixel', 'ExtraSamples',
                        'SampleFormat',
                        'Compression', 'Predictor',
                        'PhotometricInterpretation',
                        'Orientation',
                        'PlanarConfiguration',
                        'MinSampleValue', 'MaxSampleValue',
                        'XResolution', 'YResolution', 'ResolutionUnit',
                        'XPosition', 'YPosition',
                        'DocumentName',
                        'Software',
                        'HostComputer',
                        'Artist',
                        'DateTime',
                        'Make', 'Model', 'Copyright',
                        'ImageDescription',
                        ]:
                v = ifd.get_value(tag, human=True)
                if v is None:
                    continue
                if tag == 'ImageDescription' and subfile_type == 0:
                    if v.startswith('<?xml') or v[:4].lower() == '<ome':
                        try:
                            import lxml.etree
                            tree = lxml.etree.fromstring(v)
                            v = lxml.etree.tostring(tree, pretty_print=True)
                        except Exception as msg:
                            print('%s.get_info: failed to parse xml in'
                                  ' ImageDescription: %s' % (
                                      self.__class__.__name__, msg))
                        lst.append('%s:\n"""%s"""' % (tag, v))
                    else:
                        lst.append('%s:\n"""%s"""' % (tag, v))
                else:
                    lst.append('%s: %s' % (tag, v))
            if self.is_lsm and subfile_types == 0:
                lst.append('LSM info:\n"""%s"""' % (self.lsminfo))

        return '\n'.join(lst)


TiffFile = TIFFfile


class IFD:
    """ Image File Directory data structure.

    Attributes
    ----------
    entries : IFDEntry-list
    """

    def __init__(self, tiff):
        self.tiff = tiff
        self.entries = []
        self.entries_dict = {}

    def __len__(self):
        return len(self.entries)

    def append(self, entry):
        self.entries.append(entry)
        self.entries_dict[getattr(entry, 'tag_name', id(entry))] = entry

    def close(self):
        for entry in self.entries:
            entry.close()
        self.entries[:] = []
        self.entries_dict.clear()

    @property
    def memory_usage(self):
        lst = []
        for entry in self.entries:
            lst.extend(entry.memory_usage)
        return lst

    def __str__(self):
        lst = []
        for entry in self.entries:
            lst.append(str(entry))
        return '\n'.join(lst)

    def human(self):
        lst = []
        for entry in self.entries:
            lst.append(entry.human())
        return '\n'.join(lst)

    def get(self, tag_name):
        """Return IFD entry with given tag name.
        """
        return self.entries_dict.get(tag_name)

    def get_value(self, tag_name, default=None, human=False):
        """ Return the value of IFD entry with given tag name.

        When the entry does not exist, return default.
        """
        entry = self.get(tag_name)
        if entry is not None:
            value = entry.value
        else:
            if default is None:
                if tag_name in default_tag_values:
                    value = default_tag_values[tag_name]
                else:
                    value = None
                    sys.stdout.write(
                        '%s.get_value: no default value definedtiff_data.'
                        'default_tag_values dict for %r IFD tag\n' % (
                            self.__class__.__name__, tag_name))
            else:
                value = default
        if tag_name in ['StripOffsets', 'StripByteCounts']:
            if not isinstance(value, numpy.ndarray):
                value = numpy.array([value])
        if tag_name in ['BitsPerSample', 'SampleFormat']:
            samples_per_pixel = self.get_value('SamplesPerPixel')
            if not isinstance(value, numpy.ndarray):
                value = numpy.array([value] * samples_per_pixel)
            if tag_name in ['BitsPerSample']:
                value = value[:samples_per_pixel]
        if tag_name in ['ImageDescription', 'Software', 'Copyright',
                        'DocumentName', 'Model', 'Make', 'PageName',
                        'DateTime', 'Artist', 'HostComputer']:
            if value is not None:
                return value.view('|S{!s}'.format(str(value.nbytes // value.size))).tostring()
        if human:
            if tag_name == 'Compression':
                value = {1: 'Uncompressed', 2: 'CCITT1D', 3: 'Group3Fax',
                         4: 'Group4Fax',
                         5: 'LZW', 6: 'JPEG', 32773: 'PackBits'}.get(value,
                                                                     value)
            elif tag_name == 'Predictor':
                value = {1: 'None', 2: 'HorizontalDifferencing'}.get(value,
                                                                     value)
            elif tag_name == 'PhotometricInterpretation':
                value = {0: 'WhiteIsZero', 1: 'BlackIsZero', 2: 'RGB',
                         3: 'RGBPalette',
                         4: 'TransparencyMask', 5: 'CMYK', 6: 'YCbCr',
                         8: 'CIELab'}.get(value, value)
            elif tag_name == 'PlanarConfiguration':
                value = {1: 'Chunky', 2: 'Planar'}.get(value, value)
            elif tag_name == 'Orientation':
                value = {1: 'TopLeft', 2: 'TopRight', 3: 'BottomRight',
                         4: 'BottomLeft',
                         5: 'LeftTop', 6: 'RightTop', 7: 'RightBottom',
                         8: 'LeftBottom'}.get(value, value)
            elif tag_name == 'SampleFormat':
                new_value = []
                for v in value:
                    new_value.append(type2name.get(v, v))
                value = new_value
            elif tag_name == 'ResolutionUnit':
                value = {1: 'Arbitrary', 2: 'Inch', 3: 'Centimeter'}.get(value,
                                                                         value)
            elif tag_name == 'FillOrder':
                pass
        return value

    def get_sample_names(self):
        subfile_type = self.get_value('NewSubfileType')
        samples_per_pixel = self.get_value('SamplesPerPixel')
        if self.tiff.is_lsm:
            if subfile_type == 0:
                return self.tiff.lsminfo.get('data channel name')
            if subfile_type == 1 and samples_per_pixel == 3:
                return ['red', 'green', 'blue']
        return ['sample%i' % i for i in range(samples_per_pixel)]

    def get_pixel_name(self):
        subfile_type = self.get_value('NewSubfileType')
        samples_per_pixel = self.get_value('SamplesPerPixel')
        if self.tiff.is_lsm:
            if subfile_type == 0:
                return '_'.join(self.tiff.lsminfo.get('data channel name'))
            if subfile_type == 1 and samples_per_pixel == 3:
                return 'rgb'
        return 'pixel'

    def get_sample_dtypes(self):
        sample_format = self.get_value('SampleFormat')
        bits_per_sample = self.get_value('BitsPerSample')
        return [self.tiff.dtypes.get_dtype(f, b) for f, b in
                zip(sample_format, bits_per_sample)]

    def get_pixel_dtype(self):
        sample_names = self.get_sample_names()
        sample_dtypes = self.get_sample_dtypes()
        return numpy.dtype(list(zip(sample_names, sample_dtypes)))

    def get_pixel_typename(self):
        sample_dtypes = self.get_sample_dtypes()
        return '_'.join(map(str, sample_dtypes))

    def finalize(self):
        for entry in self.entries:
            for hook in IFDEntry_finalize_hooks:
                hook(entry)

    def is_contiguous(self):
        strip_offsets = self.get('StripOffsets').value
        strip_nbytes = self.get('StripByteCounts').value
        if isinstance(strip_offsets, numpy.ndarray):
            for i in range(len(strip_offsets) - 1):
                if strip_offsets[i] + strip_nbytes[i] != strip_offsets[i + 1]:
                    return False
        return True

    def get_contiguous(self, channel_name=None):
        """ Return memmap of an image.

        This operation is succesful only when image data strips are
        contiguous in memory. Return None when unsuccesful.
        """
        width = self.get('ImageWidth').value
        length = self.get('ImageLength').value
        strip_offsets = self.get('StripOffsets').value
        strip_nbytes = self.get('StripByteCounts').value
        bits_per_sample = self.get('BitsPerSample').value
        photo_interp = self.get('PhotometricInterpretation').value
        planar_config = self.get('PlanarConfiguration').value
        compression = self.get('Compression').value
        subfile_type = self.get('NewSubfileType').value
        if compression != 1:
            raise ValueError(
                'Unable to get contiguous image from compressed data')
        if not self.is_contiguous():
            raise ValueError('Image data not contiguous')

        if self.tiff.is_lsm:
            lsminfo = self.tiff.lsminfo
            # print lsminfo
            if subfile_type == 0:
                channel_names = lsminfo.get('data channel name')
            elif subfile_type == 1:  # thumbnails
                if photo_interp == 2:
                    channel_names = 'rgb'
                else:
                    raise NotImplementedError(repr(photo_interp))
            else:
                raise NotImplementedError(repr(subfile_type))
            assert planar_config == 2, repr(planar_config)
            nof_channels = self.tiff.lsmentry['DimensionChannels'][0]
            scantype = self.tiff.lsmentry['ScanType'][0]
            assert scantype == 0, repr(scantype)  # xyz-scan
            r = {}
            for i in range(nof_channels):
                if isinstance(bits_per_sample, numpy.ndarray):
                    dtype = getattr(self.dtypes,
                                    'uint%s' % (bits_per_sample[i]))
                    subdata = self.tiff.data[strip_offsets[i]: strip_offsets[i] + strip_nbytes[i]]
                    r[channel_names[i]] = subdata.view(dtype=dtype).reshape((width, length))
                else:
                    dtype = getattr(self.dtypes, 'uint%s' % (bits_per_sample))
                    r[channel_names[i]] = self.tiff.data[
                        strip_offsets:strip_offsets + strip_nbytes].view(
                            dtype=dtype).reshape((width, length))
            return r
        else:
            raise NotImplementedError(repr(self.tiff))

    def get_voxel_sizes(self):
        tiff = self.tiff
        if tiff.is_lsm:
            sample_spacing = tiff.lsminfo.get('recording sample spacing')[0]
            line_spacing = tiff.lsminfo.get('recording line spacing')[0]
            plane_spacing = tiff.lsminfo.get('recording plane spacing')[0]
            return (plane_spacing, line_spacing, sample_spacing)
        descr = self.get_value('ImageDescription', human=True)
        if descr is None:
            return (1, 1, 1)
        if descr.startswith('<?xml') or descr[:4].lower() == '<ome':
            raise NotImplementedError(
                'getting voxel sizes from OME-XML string')
        for vx, vy, vz in [('VoxelSizeX', 'VoxelSizeY', 'VoxelSizeZ'),
                           ('PixelSizeX', 'PixelSizeY', 'PixelSizeZ'),
                           ]:
            ix = descr.find(vx)
            iy = descr.find(vy)
            iz = descr.find(vz)
            if ix == -1:
                x = 1
            else:
                x = float(descr[ix:].split(None, 2)[1].strip())
            if iy == -1:
                y = 1
            else:
                y = float(descr[iy:].split(None, 2)[1].strip())
            if iz == -1:
                z = 1
            else:
                z = float(descr[iz:].split(None, 2)[1].strip())

            if -1 not in [ix, iy]:
                return (z, y, x)
        print('Could not determine voxel sizes from\n%s' % (descr))
        return (z, y, x)

    def get_pixel_sizes(self):
        tiff = self.tiff
        if tiff.is_lsm:
            sample_spacing = tiff.lsminfo.get('recording sample spacing')[0]
            line_spacing = tiff.lsminfo.get('recording line spacing')[0]
            return (line_spacing, sample_spacing)
        descr = self.get_value('ImageDescription', human=True)
        if descr is None:
            return (1, 1)
        if descr.startswith('<?xml') or descr[:4].lower() == '<ome':
            raise NotImplementedError(
                'getting pixels sizes from OME-XML string')
        for vx, vy in [('PixelSizeX', 'PixelSizeY'),
                       ('VoxelSizeX', 'VoxelSizeY'),
                       ]:
            ix = descr.find(vx)
            iy = descr.find(vy)
            if ix == -1:
                x = 1
            else:
                x = float(descr[ix:].split(None, 2)[1].strip())
            if iy == -1:
                y = 1
            else:
                y = float(descr[iy:].split(None, 2)[1].strip())
            if -1 not in [ix, iy]:
                return (y, x)
        print('Could not determine pixel sizes from\n%s' % (descr))
        return (1, 1)


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
        self.type = tiff.get_uint16(offset + 2)
        self.count = tiff.get_uint32(offset + 4)

        for hook in IFDEntry_init_hooks:
            hook(self)

        self.bytes = bytes = type2bytes.get(self.type, 0)
        if self.count == 1 and 1 <= bytes <= 4:
            self.offset = None
            value = tiff.get_value(offset + 8, self.type)
        else:
            self.offset = tiff.get_int32(offset + 8)
            value = tiff.get_values(self.offset, self.type, self.count)
        if value is not None:
            self.value = value
        self.tag_name = tag_value2name.get(self.tag, 'TAG%s'
                                           % (hex(self.tag), ))

        self.type_name = type2name.get(self.type, 'TYPE%s' % (self.type, ))

        self.memory_usage = []

        if self.offset is not None:
            self.memory_usage.append((self.offset,
                                      self.offset + self.bytes * self.count,
                                      self.tag_name))

    def close(self):
        del self.value

    @property
    def _value_str(self):
        tag_name = self.tag_name
        value = self.value
        if value is not None:
            if tag_name in ['ImageDescription', 'Software']:
                return ''.join(
                    value.view('|S%s' % (value.nbytes // value.size)))
        return value

    def __str__(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance(r, str):
                return r
        if hasattr(self, 'value'):
            return ('IFDEntry(tag=%(tag_name)s, value=%(value)r,'
                    ' count=%(count)s, offset=%(offset)s)' % (
                        self.__dict__))
        else:
            return ('IFDEntry(tag=%(tag_name)s, type=%(type_name)s,'
                    ' count=%(count)s, offset=%(offset)s)' % (
                        self.__dict__))

    def human(self):
        if hasattr(self, 'str_hook'):
            r = self.str_hook(self)
            if isinstance(r, str):
                return r
        if hasattr(self, 'value'):
            self.value_str = self._value_str
            if self.tag_name == 'ImageDescription':
                return ('IFDEntry(tag=%(tag_name)s, value="%(value_str)s",'
                        ' count=%(count)s, offset=%(offset)s)' % (
                            self.__dict__))
            else:
                return ('IFDEntry(tag=%(tag_name)s, value=%(value_str)r,'
                        ' count=%(count)s, offset=%(offset)s)' % (
                            self.__dict__))
        else:
            return ('IFDEntry(tag=%(tag_name)s, type=%(type_name)s,'
                    ' count=%(count)s, offset=%(offset)s)' % (
                        self.__dict__))

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.tiff, self.offset)


def StripOffsets_hook(ifdentry):
    if ifdentry.tag_name == 'StripOffsets':
        ifd = ifdentry.ifd
        counts = ifd.get('StripByteCounts')
        if ifdentry.offset is not None:
            for i, (count, offset) in enumerate(
                    zip(counts.value, ifdentry.value)):
                ifdentry.memory_usage.append(
                    (offset, offset + count, 'strip %s' % (i)))
        else:
            offset = ifdentry.value
            ifdentry.memory_usage.append(
                (offset, offset + counts.value, 'strip'))


# todo: TileOffsets_hook

IFDEntry_finalize_hooks.append(StripOffsets_hook)

# Register CZ LSM support:
lsm.register(locals())

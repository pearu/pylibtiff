
__all__ = ['TIFF', 'TIFFfile', 'TiffArray', 'TiffFile', 'TiffFiles', 'TiffChannelsAndFiles', 'TiffBase']

from .libtiff_ctypes import libtiff, TIFF
from .tiff import TIFFfile, TIFFimage, TiffArray
from .tiff_file import TiffFile
from .tiff_files import TiffFiles
from .tiff_channels_and_files import TiffChannelsAndFiles
from .tiff_base import TiffBase

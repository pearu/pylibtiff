
__all__ = ['TIFF', 'TIFFfile', 'TiffArray']

from .libtiff_ctypes import libtiff, TIFF
from .tiff import TIFFfile, TIFFimage, TiffArray


__all__ = ['TIFF', 'TIFFfile']

from .libtiff_ctypes import libtiff, TIFF
from .tiff import TIFFfile, TIFFimage

"""LibTiff - a Python TIFF library

.. currentmodule:: libtiff

.. autosummary::

   TIFF
   TIFFfile
   TiffArray
   TiffFile
   TiffFiles
   TiffChannelsAndFiles

"""

__autodoc__ = ['libtiff_ctypes', 'tiff', 'tiff_file',
               'tiff_files', 'tiff_channels_and_files']

__all__ = ['TIFF', 'TIFF3D', 'TIFFfile', 'TiffArray', 'TiffFile',
           'TiffFiles', 'TiffChannelsAndFiles', 'TiffBase']


from .libtiff_ctypes import libtiff, TIFF, TIFF3D  # noqa: F401
from .tiff import TIFFfile, TIFFimage, TiffArray   # noqa: F401
from .tiff_file import TiffFile
from .tiff_files import TiffFiles
from .tiff_channels_and_files import TiffChannelsAndFiles
from .tiff_base import TiffBase

# Make bitarray location available, when running from source,
import os as _os
_bitarray = _os.path.join(_os.path.dirname(__file__), 'bitarray-a1646c0')
if _os.path.exists(_bitarray):
    import sys as _sys
    _sys.path.append(_bitarray)
    import bitarray as _bitarray    # noqa: F402
    _sys.modules['libtiff.bitarray'] = _bitarray
else:
    del _bitarray

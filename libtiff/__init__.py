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

__autodoc__ = ['libtiff_ctypes', 'tiff', 'tiff_file', 'tiff_files', 'tiff_channels_and_files']

__all__ = ['TIFF', 'TIFF3D', 'TIFFfile', 'TiffArray', 'TiffFile', 'TiffFiles', 'TiffChannelsAndFiles', 'TiffBase']

from .libtiff_ctypes import libtiff, TIFF, TIFF3D
from .tiff import TIFFfile, TIFFimage, TiffArray
from .tiff_file import TiffFile
from .tiff_files import TiffFiles
from .tiff_channels_and_files import TiffChannelsAndFiles
from .tiff_base import TiffBase

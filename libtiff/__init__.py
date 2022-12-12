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

try:
    from libtiff.version import version as __version__  # noqa
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "No module named libtiff.version. This could mean "
        "you didn't install 'pylibtiff' properly. Try reinstalling ('pip "
        "install').")

from .libtiff_ctypes import libtiff, TIFF, TIFF3D  # noqa: F401
from .tiff import TIFFfile, TIFFimage, TiffArray   # noqa: F401
from .tiff_file import TiffFile
from .tiff_files import TiffFiles
from .tiff_channels_and_files import TiffChannelsAndFiles
from .tiff_base import TiffBase


=================================
PyLibTiff - a Python tiff library
=================================

:Authors:

  Pearu Peterson <pearu.peterson AT gmail DOT com>

:Website:

  http://pylibtiff.googlecode.com/

:License:

  New BSD License

History
=======

 * Started numpy.memmap wrapper of tiff files in April 2010.
 * Project published on April 22, 2009.

Download
========

The latest release can be downloaded from pylibtiff website.

The latest development code is available via SVN. To check it out,
run::

  svn checkout http://pylibtiff.googlecode.com/svn/trunk/ pylibtiff-svn
  cd pylibtiff-svn

Installation
============

To use pylibtiff, the following is required:

  * Python 2.5 or newer
  * libtiff library
  * nose for running pylibtiff tests

To install pylibtiff, unpack the archive file, change to the
pylibtiff source directory ``pylibtiff-?.?*`` (that contains setup.py
file and pylibtiff module), and run::

  python setup.py install

Testing
=======

To test pure Python pylibtiff from source directory, run::

  nosetests libtiff/tests/

Basic usage
===========

Import pylibtiff with

>>> from libtiff import *

that will provide a class TIFF to hold a tiff file:

>>> tiff = TIFF.open('filename')
>>> image = tiff.read_image()

The TIFF class provides ctypes based wrapper to the C libtiff library.

Additional documentation is available online in Pylibtiff website.

Help and bug reports
====================

You can report bugs at the pylibtiff issue tracker:

  http://code.google.com/p/pylibtiff/issues/list

Any comments and questions can be sent also to the authors.


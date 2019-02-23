=================================
PyLibTiff - a Python tiff library
=================================

:Authors:

  Pearu Peterson <pearu.peterson AT gmail DOT com>

:Website:

  https://github.com/pearu/pylibtiff/

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

  svn checkout https://github.com/pearu/pylibtiff.git pylibtiff-svn
  cd pylibtiff-svn/trunk

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

  https://github.com/pearu/pylibtiff/issues
  
Any comments and questions can be sent also to the authors.

For developers
==============

To make a release [you must be pearu],

  1. Make sure the version numbers are correct and ISRELEASED=True in
     setup.py

  2. Run

       python setup.py sdist upload -r pypi

  3. Reset ISRELEASED to False and increase version numbers in
     setup.py, rerun setup.py (to update libtiff/version.py) and
     commit changes to development repository.


#!/usr/bin/env python

CLASSIFIERS = """\
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
License :: OSI Approved
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Software Development
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
"""

import os
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

from distutils.core import Extension

if __name__=='__main__':
    from distutils.core import setup
    setup(name='pylibtiff',
          version='0.1-svn',
          author = 'Pearu Peterson',
          author_email = 'pearu.peterson@gmail.com',
          #license = 'http://pylibtiff.googlecode.com/svn/trunk/LICENSE',
          url = 'http://pylibtiff.googlecode.com',
          download_url = 'http://code.google.com/p/pylibtiff/downloads/',
          classifiers=filter(None, CLASSIFIERS.split('\n')),
          description = 'PyLibTiff: a Python wrapper to libtiff library',
          long_description = '''\
PyLibTiff? is a package that wraps the libtiff library to Python using ctypes.
''',
          platforms = ["All"],
          #package_dir = {'libtiff': '.'},
          py_modules = ['libtiff']
          )

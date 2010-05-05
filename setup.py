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

MAJOR               = 0
MINOR               = 3
MICRO               = 0
ISRELEASED          = not True
VERSION             = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

import os
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

def write_version_py(filename='libtiff/version.py'):
    cnt = """
# THIS FILE IS GENERATED FROM libtiff/setup.py
short_version='%(version)s'
version='%(version)s'
release=%(isrelease)s

if not release:
    version += '.dev'
    import os
    svn_version_file = os.path.join(os.path.dirname(__file__),
                                   '__svn_version__.py')
    svn_entries_file = os.path.join(os.path.dirname(__file__),'.svn',
                                   'entries')
    if os.path.isfile(svn_version_file):
        import imp
        svn = imp.load_module('libtiff.__svn_version__',
                              open(svn_version_file),
                              svn_version_file,
                              ('.py','U',1))
        version += svn.version
    elif os.path.isfile(svn_entries_file):
        import subprocess
        try:
            svn_version = subprocess.Popen(["svnversion", os.path.dirname (__file__)], stdout=subprocess.PIPE).communicate()[0]
        except:
            pass
        else:
            version += svn_version.strip()

print version
"""
    a = open(filename, 'w')
    try:
        a.write(cnt % {'version': VERSION, 'isrelease': str(ISRELEASED)})
    finally:
        a.close()

def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration(None,parent_package,top_path)
    config.add_subpackage('libtiff')
    config.get_version('libtiff/version.py')
    config.add_data_files(('libtiff','LICENSE'))
    return config

if __name__=='__main__':
    from numpy.distutils.core import setup

    # Rewrite the version file everytime
    if os.path.exists('libtiff/version.py'): os.remove('libtiff/version.py')
    write_version_py()

    setup(name='pylibtiff',
          #version='0.3-svn',
          author = 'Pearu Peterson',
          author_email = 'pearu.peterson@gmail.com',
          license = 'http://pylibtiff.googlecode.com/svn/trunk/LICENSE',
          url = 'http://pylibtiff.googlecode.com',
          download_url = 'http://code.google.com/p/pylibtiff/downloads/',
          classifiers=filter(None, CLASSIFIERS.split('\n')),
          description = 'PyLibTiff: a Python tiff library.',
          long_description = '''\
PyLibTiff? is a Python package that provides the following modules:

   libtiff - a wrapper of C libtiff library using ctypes.
   tiff - a numpy.memmap view of tiff files.
''',
          platforms = ["All"],
          #packages = ['libtiff'],
          #package_dir = {'libtiff': 'libtiff'},
          configuration = configuration,
          )

#!/usr/bin/env python
import os
import sys
import subprocess
import textwrap
import warnings

CLASSIFIERS = """\
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
License :: OSI Approved
Programming Language :: Python
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Topic :: Scientific/Engineering
Topic :: Software Development
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
"""

MAJOR = 0
MINOR = 4
MICRO = 5
ISRELEASED = False
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')


def git_version():
    # Copied from scipy/setup.py
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        GIT_REVISION = out.strip().decode('ascii')
    except OSError:
        GIT_REVISION = "Unknown"

    return GIT_REVISION


def get_version_info():
    # Copied from scipy/setup.py
    FULLVERSION = VERSION
    if os.path.exists('.git'):
        GIT_REVISION = git_version()
    elif os.path.exists('libtiff/version.py'):
        # must be a source distribution, use existing version file
        # load it as a separate module to not load libtiff/__init__.py
        import imp
        version = imp.load_source('libdiff.version', 'libtiff/version.py')
        GIT_REVISION = version.git_revision
    else:
        GIT_REVISION = "Unknown"

    if not ISRELEASED:
        FULLVERSION += '.dev0+' + GIT_REVISION[:7]

    return FULLVERSION, GIT_REVISION


def write_version_py(filename='libtiff/version.py'):
    # Copied from scipy/setup.py
    cnt = """
# THIS FILE IS GENERATED FROM PYLIBTIFF SETUP.PY
short_version = '%(version)s'
version = '%(version)s'
full_version = '%(full_version)s'
git_revision = '%(git_revision)s'
release = %(isrelease)s
if not release:
    version = full_version
"""
    FULLVERSION, GIT_REVISION = get_version_info()

    a = open(filename, 'w')
    try:
        a.write(cnt % {'version': VERSION,
                       'full_version': FULLVERSION,
                       'git_revision': GIT_REVISION,
                       'isrelease': str(ISRELEASED)})
    finally:
        a.close()


def parse_setuppy_commands():
    # Copied from scipy/setup.py
    args = sys.argv[1:]

    if not args:
        return True

    info_commands = ['--help-commands', '--name', '--version', '-V',
                     '--fullname', '--author', '--author-email',
                     '--maintainer', '--maintainer-email', '--contact',
                     '--contact-email', '--url', '--license', '--description',
                     '--long-description', '--platforms', '--classifiers',
                     '--keywords', '--provides', '--requires', '--obsoletes']

    for command in info_commands:
        if command in args:
            return False

    good_commands = ('develop', 'sdist', 'build', 'build_ext', 'build_py',
                     'build_clib', 'build_scripts', 'bdist_wheel', 'bdist_rpm',
                     'bdist_wininst', 'bdist_msi', 'bdist_mpkg',
                     'build_sphinx')

    for command in good_commands:
        if command in args:
            return True

    if 'install' in args:
        print(textwrap.dedent("""
            Note: if you need reliable uninstall behavior, then install
            with pip instead of using `setup.py install`:
              - `pip install .`       (from a git repo or downloaded source
                                       release)
              - `pip install pylibtiff`   (last PyLibTiff release on PyPI)
            """))
        return True

    if '--help' in args or '-h' in sys.argv[1]:
        print(textwrap.dedent("""
            PyLibTiff-specific help
            -----------------------
            To install PyLibTiff from here with reliable uninstall, we
            recommend that you use `pip install .`. To install the
            latest PyLibTiff release from PyPI, use `pip install
            pylibtiff`.

            If you are sure that you have run into a bug, please
            report it at https://github.com/pearu/pylibtiff/issues.

            Setuptools commands help
            ------------------------
            """))
        return False

    # The following commands aren't supported.  They can only be executed when
    # the user explicitly adds a --force command-line argument.
    bad_commands = dict(
        test="""
            `setup.py test` is not supported.  Use one of the following
            instead:
              - `pytest -sv libtiff/`
            """,
        upload="""
            `setup.py upload` is not supported, because it's insecure.
            Instead, build what you want to upload and upload those files
            with `twine upload -s <filenames>` instead.
            """,
        upload_docs="`setup.py upload_docs` is not supported",
        easy_install="`setup.py easy_install` is not supported",
        clean="""
        `setup.py clean` is not supported, use one of the following instead:
          - `git clean -xdf` (cleans all files)
          - `git clean -Xdf` (cleans all versioned files, doesn't touch
             files that aren't checked into the git repo)
        """,
        check="`setup.py check` is not supported",
        register="`setup.py register` is not supported",
        bdist_dumb="`setup.py bdist_dumb` is not supported",
        bdist="`setup.py bdist` is not supported",
        flake8="`setup.py flake8` is not supported, use flake8 standalone",
        )
    bad_commands['nosetests'] = bad_commands['test']
    for command in ('upload_docs', 'easy_install', 'bdist', 'bdist_dumb',
                    'register', 'check', 'install_data', 'install_headers',
                    'install_lib', 'install_scripts', ):
        bad_commands[command] = "`setup.py %s` is not supported" % command

    for command in bad_commands.keys():
        if command in args:
            print(textwrap.dedent(bad_commands[command]) +
                  "\nAdd `--force` to your command to use it anyway if you "
                  "must (unsupported).\n")
            sys.exit(1)

    # Commands that do more than print info, but also don't need Cython and
    # template parsing.
    other_commands = ['egg_info', 'install_egg_info', 'rotate']
    for command in other_commands:
        if command in args:
            return False

    # If we got here, we didn't detect what setup.py command was given
    warnings.warn("Unrecognized setuptools command")
    return True


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration(None, parent_package, top_path)
    config.add_subpackage('libtiff')
    config.get_version('libtiff/version.py')
    config.add_data_files(('libtiff', 'LICENSE'))
    return config


def setup_package():
    # Rewrite the version file every time
    write_version_py()

    try:
        import numpy     # noqa: F401
    except ImportError:  # We do not have numpy installed
        build_requires = ['numpy>=1.13.3']
    else:
        build_requires = (['numpy>=1.13.3'] if 'bdist_wheel' in sys.argv[1:]
                          else [])

    metadata = dict(
        name='pylibtiff',
        author='Pearu Peterson',
        author_email='pearu.peterson@gmail.com',
        license='https://github.com/pearu/pylibtiff/blob/master/LICENSE',
        url='https://github.com/pearu/pylibtiff',
        # download_url = 'http://code.google.com/p/pylibtiff/downloads/',
        classifiers=[_f for _f in CLASSIFIERS.split('\n') if _f],
        description='PyLibTiff: a Python tiff library.',
        long_description='''\

PyLibTiff? is a Python package that provides the following modules:

   libtiff - a wrapper of C libtiff library using ctypes.
   tiff - a numpy.memmap view of tiff files.
''',
        platforms=["All"],
        setup_requires=build_requires,
        install_requires=build_requires,
<<<<<<< HEAD
        python_requires='>=3.8',
=======
        extras_require={
            'bitarray': ['bitarray'],
        },
        python_requires='>=2.7',
>>>>>>> master
    )
    if "--force" in sys.argv:
        run_build = True
        sys.argv.remove('--force')
    else:
        run_build = parse_setuppy_commands()

    from setuptools import setup

    if run_build:
        from numpy.distutils.core import setup  # noqa: F811
        metadata['configuration'] = configuration
    else:
        metadata['version'] = get_version_info()[0]

    setup(**metadata)


if __name__ == '__main__':
    setup_package()

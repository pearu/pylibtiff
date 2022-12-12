#!/usr/bin/env python
import sys
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
            print(textwrap.dedent(bad_commands[command]) + "\nAdd `--force` to your command to use it anyway "
                  "if you must (unsupported).\n")
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
    config.add_data_files(('libtiff', 'LICENSE'))
    return config


def setup_package():
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
        python_requires='>=3.8',
        extras_require={
            'bitarray': ['bitarray'],
        },
    )
    if "--force" in sys.argv:
        run_build = True
        sys.argv.remove('--force')
    else:
        run_build = parse_setuppy_commands()

    from setuptools import setup

    try:
        # HACK: https://github.com/pypa/setuptools_scm/issues/190#issuecomment-351181286
        # Stop setuptools_scm from including all repository files
        import setuptools_scm.integration
        setuptools_scm.integration.find_files = lambda _: []
    except ImportError:
        pass

    if run_build:
        from numpy.distutils.core import setup  # noqa: F811
        metadata['configuration'] = configuration

    setup(**metadata)


if __name__ == '__main__':
    setup_package()

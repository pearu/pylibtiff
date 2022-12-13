#!/usr/bin/env python

from numpy.distutils.core import setup  # noqa: F811

try:
    # HACK: https://github.com/pypa/setuptools_scm/issues/190#issuecomment-351181286
    # Stop setuptools_scm from including all repository files
    import setuptools_scm.integration
    setuptools_scm.integration.find_files = lambda _: []
except ImportError:
    pass


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration(None, parent_package, top_path)
    config.add_subpackage('libtiff')
    config.add_data_files(('libtiff', 'LICENSE'))
    return config


def setup_package():
    with open("README.md", "r") as readme:
        long_description = readme.read()

    metadata = dict(
        name='pylibtiff',
        author='Pearu Peterson',
        author_email='pearu.peterson@gmail.com',
        license='https://github.com/pearu/pylibtiff/blob/master/LICENSE',
        url='https://github.com/pearu/pylibtiff',
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Topic :: Scientific/Engineering",
            "Topic :: Software Development",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: POSIX",
            "Operating System :: Unix",
            "Operating System :: MacOS",
        ],
        description='PyLibTiff: a Python tiff library.',
        long_description=long_description,
        long_description_content_type='text/markdown',
        platforms=["All"],
        install_requires=['numpy>=1.13.3'],
        python_requires='>=3.8',
        extras_require={
            'bitarray': ['bitarray'],
        },
        configuration=configuration,
    )
    setup(**metadata)


if __name__ == '__main__':
    setup_package()

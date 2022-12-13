#!/usr/bin/env python

import os
from setuptools import find_packages, Extension, setup
import numpy as np

try:
    # HACK: https://github.com/pypa/setuptools_scm/issues/190#issuecomment-351181286
    # Stop setuptools_scm from including all repository files
    import setuptools_scm.integration
    setuptools_scm.integration.find_files = lambda _: []
except ImportError:
    pass


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
        install_requires=['numpy>=1.13.3'],
        python_requires='>=3.8',
        extras_require={
            'bitarray': ['bitarray'],
        },
        include_package_data=True,
        packages=find_packages(),
        ext_modules=[
            Extension(name="libtiff.bittools",
                      sources=[os.path.join("libtiff", "src", "bittools.c")],
                      include_dirs=[np.get_include()]),
            Extension(name="libtiff.tif_lzw",
                      sources=[os.path.join("libtiff", "src", "tif_lzw.c")],
                      include_dirs=[np.get_include()]),
        ],
        entry_points={
            'console_scripts': [
                'libtiff.info = libtiff.scripts.info:main',
                'libtiff.convert = libtiff.scripts.convert:main',
            ],
        },
    )
    setup(**metadata)


if __name__ == '__main__':
    setup_package()

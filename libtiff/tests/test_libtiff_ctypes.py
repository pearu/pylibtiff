import pytest
import numpy as np
from libtiff import TIFFimage

lt = pytest.importorskip('libtiff.libtiff_ctypes')


def test_issue69(tmp_path):
    itype = np.uint32
    image = np.array([[[1, 2, 3], [4, 5, 6]]], itype)
    fn = str(tmp_path / "issue69.tif")
    tif = TIFFimage(image)
    tif.write_file(fn)
    del tif
    tif = lt.TIFF3D.open(fn)
    tif.close()

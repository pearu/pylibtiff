import sys

import numpy
import pytest

from libtiff import TIFF, TIFFfile, TIFFimage
from libtiff.scripts import convert, info

darwin_mmap_resize = pytest.mark.skipif(sys.platform == "darwin", reason="OSX can't resize mmap")


def _write_ctypes(fn, image):
    """Write a TIFF file without ImageDescription, one page per 2-D image."""
    tif = TIFF.open(fn, 'w')
    for page in image.reshape((-1,) + image.shape[-2:]):
        tif.SetField('RowsPerStrip', image.shape[-2])
        tif.write_image(page)
    tif.close()
    return str(fn)


def _run(monkeypatch, main, name, *args):
    monkeypatch.setattr(sys, 'argv', [name] + list(args))
    main()


def test_info(tmp_path, monkeypatch, capsys):
    fn = _write_ctypes(tmp_path / 'image.tif', numpy.zeros((5, 7), numpy.uint16))
    _run(monkeypatch, info.main, 'libtiff.info', '-i', fn)
    out = capsys.readouterr().out.splitlines()
    assert 'IFDEntry(tag=ImageWidth, value=np.uint16(7), count=1, offset=None)' in out
    assert 'data is contiguous: True' in out
    assert 'memory usage is ok' in out
    assert 'Sample 0 in subfile 0:' in out
    assert '  shape= (1, 5, 7)' in out
    assert '  dtype= uint16' in out
    assert '  pixel_sizes= (1, 1)' in out


def test_info_all_ifds(tmp_path, monkeypatch, capsys):
    fn = _write_ctypes(tmp_path / 'stack.tif', numpy.zeros((2, 3, 4), numpy.uint8))
    _run(monkeypatch, info.main, 'libtiff.info', '-i', fn, '--memory-usage', '--ifd')
    out = capsys.readouterr().out.splitlines()
    assert 'Memory usage:' in out
    assert 'IFD0:' in out
    assert 'IFD1:' in out
    assert 'data is contiguous: False' in out
    assert '  shape= (2, 3, 4)' in out


@pytest.mark.xfail(strict=True, reason="IFDEntry.human joins the bytes ImageDescription as str")
@darwin_mmap_resize
def test_info_human(tmp_path, monkeypatch, capsys):
    fn = str(tmp_path / 'stack.tif')
    TIFFimage(numpy.zeros((2, 3, 4), numpy.uint8), description='a description').write_file(fn)
    _run(monkeypatch, info.main, 'libtiff.info', '-i', fn, '--human')
    out = capsys.readouterr().out
    assert 'a description' in out


def test_info_requires_input_path(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        _run(monkeypatch, info.main, 'libtiff.info')
    assert 'Expected --input-path' in capsys.readouterr().err


@pytest.mark.parametrize("compression", [None, 'lzw'])
@darwin_mmap_resize
def test_convert(tmp_path, monkeypatch, compression):
    image = numpy.arange(5 * 7, dtype=numpy.int16).reshape(5, 7)
    fn = _write_ctypes(tmp_path / 'image.tif', image)
    monkeypatch.chdir(tmp_path)
    args = ['-i', fn]
    if compression:
        args += ['--compression', compression]
    _run(monkeypatch, convert.main, 'libtiff.convert', *args)

    # the output is written to the current directory
    tif = TIFFfile(str(tmp_path / 'image_sample0_None.tif'))
    assert tif.IFD[0].get_value('Compression') == (5 if compression else 1)
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image[numpy.newaxis])
    tif.close()


@pytest.mark.xfail(strict=True, reason="libtiff.convert ignores --output-path")
@darwin_mmap_resize
def test_convert_output_path(tmp_path, monkeypatch):
    image = numpy.arange(5 * 7, dtype=numpy.int16).reshape(5, 7)
    fn = _write_ctypes(tmp_path / 'image.tif', image)
    monkeypatch.chdir(tmp_path)
    _run(monkeypatch, convert.main, 'libtiff.convert', '-i', fn, '-o', str(tmp_path / 'out_%(channel_name)s.tif'))
    assert (tmp_path / 'out_sample0.tif').exists()


@pytest.mark.xfail(strict=True, reason="libtiff.convert joins bytes ImageDescription values as str")
@darwin_mmap_resize
def test_convert_with_description(tmp_path, monkeypatch):
    image = numpy.arange(2 * 5 * 7, dtype=numpy.int16).reshape(2, 5, 7)
    fn = str(tmp_path / 'stack.tif')
    TIFFimage(image, description='a description').write_file(fn)
    monkeypatch.chdir(tmp_path)
    _run(monkeypatch, convert.main, 'libtiff.convert', '-i', fn)
    tif = TIFFfile(str(tmp_path / 'stack_sample0_None.tif'))
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image)
    tif.close()


@pytest.mark.skipif(sys.platform == "win32", reason="the output file name contains the slice")
@pytest.mark.xfail(strict=True, reason="libtiff.convert --slice is a no-op (exec does not rebind the local)")
@darwin_mmap_resize
def test_convert_slice(tmp_path, monkeypatch):
    image = numpy.arange(5 * 7, dtype=numpy.int16).reshape(5, 7)
    fn = _write_ctypes(tmp_path / 'image.tif', image)
    monkeypatch.chdir(tmp_path)
    _run(monkeypatch, convert.main, 'libtiff.convert', '-i', fn, '--slice', ':,1:3')
    tif = TIFFfile(str(tmp_path / 'image_sample0_:,1:3.tif'))
    numpy.testing.assert_array_equal(tif.get_tiff_array()[:], image[numpy.newaxis, 1:3])
    tif.close()

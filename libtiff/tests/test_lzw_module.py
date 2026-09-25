"""Tests for the obsolete pure-Python libtiff.lzw module."""

import importlib

import pytest


@pytest.mark.xfail(strict=True, reason="libtiff.lzw imports bittools as a top-level module")
def test_lzw_module_import():
    importlib.import_module('libtiff.lzw')

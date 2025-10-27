# -*- coding: utf-8 -*-
"""Unit tests for advanced statistical plugins added in the integration task.

This test uses a deterministic byte sequence so outputs are reproducible.
"""

import time
from patternlab.plugin_api import BytesView, TestResult
from patternlab.plugins.diehard_birthday_spacings import BirthdaySpacingsTest
from patternlab.plugins.diehard_overlapping_sums import OverlappingSumsTest
from patternlab.plugins.diehard_3d_spheres import ThreeDSpheresTest
from patternlab.plugins.testu01_smallcrush import SmallCrushAdapter
from patternlab.plugins.dft_spectral_advanced import DFTSpectralAdvancedTest
from patternlab.plugins.hurst_exponent import HurstExponentTest


def _deterministic_bytes(length=4096):
    return bytes([(i * 31 + 7) % 256 for i in range(length)])


def _assert_basic_tr(tr):
    assert isinstance(tr, TestResult)
    assert tr.test_name is not None
    # time_ms and bytes_processed should exist (may be None)
    assert hasattr(tr, "time_ms")
    assert hasattr(tr, "bytes_processed")


def test_birthday_spacings_run_and_streaming():
    data = _deterministic_bytes(4096)
    bv = BytesView(data)
    plugin = BirthdaySpacingsTest()
    # direct run
    tr = plugin.run(bv, {"n": 512, "m": 2 ** 16, "downsample": 1, "alpha": 0.01})
    _assert_basic_tr(tr)
    # streaming path
    plugin.update(data[:2048], {})
    plugin.update(data[2048:], {})
    tr2 = plugin.finalize({})
    _assert_basic_tr(tr2)


def test_overlapping_sums_run_and_streaming():
    data = _deterministic_bytes(8192)
    bv = BytesView(data)
    plugin = OverlappingSumsTest()
    tr = plugin.run(bv, {"window": 16, "bins": 64, "downsample": 1, "alpha": 0.01})
    _assert_basic_tr(tr)
    # streaming
    chunk = data[:4096]
    plugin.update(chunk, {"max_buffer_bytes": 1 << 20})
    tr2 = plugin.finalize({"window": 16, "bins": 64})
    _assert_basic_tr(tr2)


def test_3d_spheres_run_and_streaming():
    data = _deterministic_bytes(16384)
    bv = BytesView(data)
    plugin = ThreeDSpheresTest()
    tr = plugin.run(bv, {"radius": 0.4, "group_words": 3, "downsample": 2, "bins": 8, "alpha": 0.01})
    _assert_basic_tr(tr)
    # streaming
    plugin.update(data[:8000], {})
    plugin.update(data[8000:], {})
    tr2 = plugin.finalize({})
    _assert_basic_tr(tr2)


def test_testu01_smallcrush_subset():
    data = _deterministic_bytes(4096)
    bv = BytesView(data)
    plugin = SmallCrushAdapter()
    tr = plugin.run(bv, {"downsample": 1, "alpha": 0.01})
    _assert_basic_tr(tr)
    # ensure p_values has at least one subtest
    assert isinstance(tr.p_values, dict)
    assert len(tr.p_values) >= 1
    # streaming
    plugin.update(data[:2000], {})
    plugin.update(data[2000:], {})
    tr2 = plugin.finalize({})
    _assert_basic_tr(tr2)


def test_dft_spectral_advanced_basic():
    data = _deterministic_bytes(8192)
    bv = BytesView(data)
    plugin = DFTSpectralAdvancedTest()
    tr = plugin.run(bv, {"mode": "bits", "window_size": 1024, "hop": 512, "max_windows": 16, "alpha": 0.01})
    _assert_basic_tr(tr)
    # streaming
    plugin.update(data[:4096], {"mode": "bits"})
    plugin.update(data[4096:], {"mode": "bits"})
    tr2 = plugin.finalize({"mode": "bits"})
    _assert_basic_tr(tr2)


def test_hurst_exponent_basic():
    data = _deterministic_bytes(8192)
    bv = BytesView(data)
    plugin = HurstExponentTest()
    tr = plugin.run(bv, {"method": "rs", "min_window": 8, "alpha": 0.01})
    _assert_basic_tr(tr)
    # streaming
    plugin.update(data[:3000], {})
    plugin.update(data[3000:], {})
    tr2 = plugin.finalize({})
    _assert_basic_tr(tr2)
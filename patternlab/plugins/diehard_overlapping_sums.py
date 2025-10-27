# -*- coding: utf-8 -*-
"""Dieharder Overlapping Sums test plugin."""

from typing import Dict, Any, Optional
import time
import numpy as np
from scipy import stats

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class OverlappingSumsTest(TestPlugin):
    """Simplified Overlapping Sums test.

    Computes sums of overlapping 32-bit words modulo a window and compares distribution
    with expected uniform distribution using chi-square.

    Parameters:
      - window: window size for overlapping sum (default: 32)
      - bins: number of histogram bins (default: 256)
      - downsample: sample every k-th 32-bit word (default: 1)
      - max_buffer_bytes: internal buffer limit for streaming (default: 1<<20)
    """

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None

    def describe(self) -> str:
        return "Dieharder Overlapping Sums (approx.)"

    def _compute_sums(self, data_bytes: bytes, window: int, downsample: int) -> np.ndarray:
        if len(data_bytes) < 4:
            return np.array([], dtype=np.uint32)
        arr = np.frombuffer(data_bytes, dtype=np.uint32)
        if downsample > 1:
            arr = arr[::downsample]
        # compute overlapping sums modulo 2**32 over sliding window
        if window <= 1 or arr.size == 0:
            return arr.astype(np.uint64)  # treat single words as sums
        sums = np.empty(max(0, arr.size - window + 1), dtype=np.uint64)
        if sums.size == 0:
            return np.array([], dtype=np.uint64)
        # rolling sum efficient using cumulative sum
        # Ensure the prepended zero has matching dtype so numpy preserves numeric dtype
        cumsum = np.concatenate((np.array([0], dtype=np.uint64), arr.astype(np.uint64).cumsum()))
        sums = (cumsum[window:] - cumsum[:-window]) & np.uint64(0xFFFFFFFF)
        return sums

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        window = int(params.get("window", 32))
        bins = int(params.get("bins", 256))
        downsample = int(params.get("downsample", 1))

        sums = self._compute_sums(bts, window, downsample)
        n = len(sums)
        p_value = None
        chi2 = None
        if n > 0:
            hist, edges = np.histogram(sums, bins=bins, range=(0, 2 ** 32))
            expected = n / float(bins)
            # use chi-square test; avoid zero-expected issues
            with np.errstate(divide='ignore', invalid='ignore'):
                chi2 = float(((hist - expected) ** 2 / expected).sum())
            df = bins - 1
            p_value = 1.0 - stats.chi2.cdf(chi2, df)

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_overlapping_sums"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"chi2": chi2 if p_value is not None else None},
            metrics={"n": int(n), "bins": bins, "window": window, "downsample": downsample},
            time_ms=(end - self._start) * 1000.0,
            bytes_processed=len(bts),
        )
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if self._start is None:
            self._start = time.time()
        self._buf.extend(chunk)
        self._count_bytes += len(chunk)
        max_buf = int(params.get("max_buffer_bytes", 1 << 20))
        if len(self._buf) > max_buf:
            # drop oldest half to keep bounded memory while preserving some overlap
            half = len(self._buf) // 2
            self._buf = self._buf[half:]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        window = int(params.get("window", 32))
        bins = int(params.get("bins", 256))
        downsample = int(params.get("downsample", 1))
        sums = self._compute_sums(bts, window, downsample)
        n = len(sums)
        p_value = None
        chi2 = None
        if n > 0:
            hist, edges = np.histogram(sums, bins=bins, range=(0, 2 ** 32))
            expected = n / float(bins)
            with np.errstate(divide='ignore', invalid='ignore'):
                chi2 = float(((hist - expected) ** 2 / expected).sum())
            df = bins - 1
            p_value = 1.0 - stats.chi2.cdf(chi2, df)

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_overlapping_sums"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"chi2": chi2 if p_value is not None else None},
            metrics={"n": int(n), "bins": bins, "window": window, "downsample": downsample},
            time_ms=(end - (self._start or end)) * 1000.0,
            bytes_processed=self._count_bytes,
        )
        # reset
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        return tr
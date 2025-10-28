# -*- coding: utf-8 -*-
"""Dieharder Birthday Spacings test plugin."""

from typing import Dict, Any, List, Optional
import math
import numpy as np
from scipy import stats
import time

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView


class BirthdaySpacingsTest(TestPlugin):
    """Simplified Birthday Spacings test adapted for Pattern Analyzer.

    Streaming supported via update()/finalize().
    Parameters:
      - n: number of birthdays to sample (default: 512)
      - m: birthday space size (default: 2**24)
      - downsample: sample every k-th 32-bit word (default: 1)
    """

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None

    def describe(self) -> str:
        return "Dieharder Birthday Spacings (approx.)"

    def _extract_birthdays(self, bts: bytes, n: int, downsample: int = 1) -> np.ndarray:
        arr = np.frombuffer(bts, dtype=np.uint32)
        if downsample > 1:
            arr = arr[::downsample]
        if arr.size < n:
            n = arr.size
        if n <= 0:
            return np.array([], dtype=np.uint32)
        return arr[:n] % self._m

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        self._m = int(params.get("m", 2 ** 24))
        downsample = int(params.get("downsample", 1))
        default_n = int(params.get("n", 512))
        arr = self._extract_birthdays(bts, default_n, downsample)
        n = arr.size
        R = 0
        p_value = None
        lam = None
        if n >= 2:
            s = np.sort(arr)
            spacings = np.diff(np.concatenate((s, s[:1] + self._m)))
            # Count repeated spacings
            unique, counts = np.unique(spacings, return_counts=True)
            R = int(np.sum(counts[counts > 1] - 1))
            # Poisson approximation for R's mean
            lam = (n ** 3) / (4.0 * self._m) if self._m > 0 else float(n)
            p_value = 1.0 - stats.poisson.cdf(R - 1, lam)
        else:
            p_value = None

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_birthday_spacings"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"R": float(R) if p_value is not None else None},
            metrics={"R": R, "n": int(n), "m": int(self._m), "lambda": lam if n >= 2 else None},
            time_ms=(end - self._start) * 1000.0,
            bytes_processed=len(bts),
        )
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if self._start is None:
            self._start = time.time()
        self._buf.extend(chunk)
        self._count_bytes += len(chunk)
        # Keep buffer bounded: allow at most params.get("max_buffer_bytes", 1<<20)
        max_buf = int(params.get("max_buffer_bytes", 1 << 20))
        if len(self._buf) > max_buf:
            # simple downsample: keep every other 32-bit word to reduce memory
            arr = np.frombuffer(self._buf, dtype=np.uint32)
            arr = arr[::2]
            self._buf = bytearray(arr.tobytes())

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        # run test on accumulated buffer
        bts = bytes(self._buf)
        self._m = int(params.get("m", 2 ** 24))
        downsample = int(params.get("downsample", 1))
        default_n = int(params.get("n", 512))
        arr = self._extract_birthdays(bts, default_n, downsample)
        n = arr.size
        R = 0
        p_value = None
        lam = None
        if n >= 2:
            s = np.sort(arr)
            spacings = np.diff(np.concatenate((s, s[:1] + self._m)))
            unique, counts = np.unique(spacings, return_counts=True)
            R = int(np.sum(counts[counts > 1] - 1))
            lam = (n ** 3) / (4.0 * self._m) if self._m > 0 else float(n)
            p_value = 1.0 - stats.poisson.cdf(R - 1, lam)

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_birthday_spacings"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"R": float(R) if p_value is not None else None},
            metrics={"R": R, "n": int(n), "m": int(self._m), "lambda": lam},
            time_ms=(end - (self._start or end)) * 1000.0,
            bytes_processed=self._count_bytes,
        )
        # reset buffer for re-use
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        return tr
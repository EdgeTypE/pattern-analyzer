# -*- coding: utf-8 -*-
"""Hurst exponent test plugin.

Implements two methods to estimate Hurst exponent:
 - R/S (rescaled range) method (default)
 - DFA (detrended fluctuation analysis) as optional method

Streaming: update()/finalize() supported. Input bytes are treated as uint8 samples
centered to zero; downsampling and max_buffer_bytes limits are available.
Returns TestResult with estimated H and diagnostics.
"""

from typing import Dict, Any, Optional, List
import time
import math
import numpy as np
from scipy import stats

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


def _rs_hurst(ts: np.ndarray, min_window: int = 8, max_window: Optional[int] = None) -> Optional[float]:
    n = ts.size
    if n < min_window * 2:
        return None
    if max_window is None:
        max_window = n // 2
    # choose window sizes logarithmically
    sizes = np.unique(np.floor(np.logspace(math.log10(min_window), math.log10(max_window), num=10)).astype(int))
    sizes = sizes[sizes >= min_window]
    rs_vals = []
    ns = []
    for s in sizes:
        if s < 2 or s > n:
            continue
        # split into blocks of size s
        k = n // s
        if k < 1:
            continue
        seg_rs = []
        for i in range(k):
            seg = ts[i * s:(i + 1) * s]
            if seg.size < 2:
                continue
            mean = seg.mean()
            Y = np.cumsum(seg - mean)
            R = Y.max() - Y.min()
            S = seg.std(ddof=0)
            if S <= 0:
                continue
            seg_rs.append(R / S)
        if len(seg_rs) == 0:
            continue
        rs_vals.append(np.mean(seg_rs))
        ns.append(s)
    if len(ns) < 2:
        return None
    log_ns = np.log10(np.array(ns))
    log_rs = np.log10(np.array(rs_vals))
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_ns, log_rs)
    return float(slope)


def _dfa_hurst(ts: np.ndarray, min_window: int = 8, max_window: Optional[int] = None) -> Optional[float]:
    n = ts.size
    if n < min_window * 2:
        return None
    if max_window is None:
        max_window = n // 2
    sizes = np.unique(np.floor(np.logspace(math.log10(min_window), math.log10(max_window), num=10)).astype(int))
    sizes = sizes[sizes >= min_window]
    F = []
    ns = []
    X = np.cumsum(ts - ts.mean())
    for s in sizes:
        if s < 2 or s > n:
            continue
        k = n // s
        if k < 1:
            continue
        rms = []
        for i in range(k):
            seg = X[i * s:(i + 1) * s]
            if seg.size < 2:
                continue
            # linear detrend
            x = np.arange(seg.size)
            slope, intercept, r, p, stderr = stats.linregress(x, seg)
            fit = slope * x + intercept
            diff = seg - fit
            rms.append(np.sqrt(np.mean(diff ** 2)))
        if len(rms) == 0:
            continue
        F.append(np.mean(rms))
        ns.append(s)
    if len(ns) < 2:
        return None
    log_ns = np.log10(np.array(ns))
    log_F = np.log10(np.array(F))
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_ns, log_F)
    return float(slope)


class HurstExponentTest(TestPlugin):
    """Estimate Hurst exponent using R/S or DFA.

    Parameters:
      - method: "rs" or "dfa" (default "rs")
      - min_window: minimum window size for analysis (default 8)
      - max_window: maximum window size (default n//2)
      - downsample: keep every k-th sample (default 1)
      - mode: "bytes" or "bits" (default "bytes") -- interprets input samples
      - max_buffer_bytes: memory cap for streaming (default 1<<20)
    """

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None

    def describe(self) -> str:
        return "Hurst exponent estimation (R/S and DFA)"

    def _samples_from_bytes(self, bts: bytes, mode: str, downsample: int) -> np.ndarray:
        if mode == "bits":
            try:
                arr = np.frombuffer(bts, dtype=np.uint8)
                bits = np.unpackbits(arr).astype(np.float64)
                if downsample > 1:
                    bits = bits[::downsample]
                # map {0,1} -> {-1,1}
                return bits * 2.0 - 1.0
            except Exception:
                arr = np.frombuffer(bts, dtype=np.uint8)
                bits = np.unpackbits(arr).astype(np.float64)
                return bits * 2.0 - 1.0
        else:
            arr = np.frombuffer(bts, dtype=np.uint8).astype(np.float64)
            if downsample > 1:
                arr = arr[::downsample]
            # center
            return arr - arr.mean() if arr.size > 0 else arr

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        method = str(params.get("method", "rs"))
        min_window = int(params.get("min_window", 8))
        max_window = params.get("max_window", None)
        downsample = int(params.get("downsample", 1))
        mode = str(params.get("mode", "bytes"))

        samples = self._samples_from_bytes(bts, mode, downsample)
        n = samples.size
        hurst = None
        method_used = method
        if method == "rs":
            hurst = _rs_hurst(samples, min_window=min_window, max_window=max_window)
        else:
            hurst = _dfa_hurst(samples, min_window=min_window, max_window=max_window)
            method_used = "dfa"

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "hurst_exponent"),
            passed=(hurst is None) or (0.0 <= hurst <= 1.0),
            p_value=None,
            category="longrange",
            p_values={"hurst": hurst} if hurst is not None else {},
            metrics={"n": int(n), "method": method_used, "min_window": int(min_window), "downsample": int(downsample)},
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
            # downsample buffer by keeping every other byte to reduce memory
            arr = np.frombuffer(self._buf, dtype=np.uint8)
            arr = arr[::2]
            self._buf = bytearray(arr.tobytes())

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        bv = BytesView(bts)
        tr = self.run(bv, params)
        # reset
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        return tr
# -*- coding: utf-8 -*-
"""Mutual Information and Pointwise Mutual Information plugin.

Streaming-supported TestPlugin that accumulates symbol and pair counts and computes:
  - Mutual Information I(X;Y) for adjacent-symbol pairs (first-order)
  - Pointwise Mutual Information (PMI) summary stats (min/median/max)

Parameters accepted in params dict:
  - mode: "bytes" (default) or "bits"
  - downsample: integer >=1 (default 1)
  - max_buffer_bytes: memory cap for streaming (default 1<<20)
  - name: optional test name
"""

from typing import Dict, Any, Optional
import time
import math
import numpy as np

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class MutualInformationTest(TestPlugin):
    """Compute I(X;Y) and PMI summary for first-order symbol sequences."""

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._single_counts = None
        self._pair_counts = None
        self._alphabet_size = None
        self._prev_symbol = None

    def describe(self) -> str:
        return "Mutual Information I(X;Y) and PMI statistics (first-order adjacency)"

    def _ensure_counts(self, mode: str):
        if mode == "bits":
            size = 2
        else:
            size = 256
        if self._single_counts is None or self._alphabet_size != size:
            self._alphabet_size = size
            self._single_counts = np.zeros(size, dtype=np.int64)
            self._pair_counts = np.zeros((size, size), dtype=np.int64)

    def _process_array(self, arr: np.ndarray, downsample: int):
        if downsample > 1:
            arr = arr[::downsample]
        if arr.size == 0:
            return
        vals, cnts = np.unique(arr, return_counts=True)
        self._single_counts[vals] += cnts
        # pairs
        if self._prev_symbol is not None:
            first = np.array([self._prev_symbol], dtype=arr.dtype)
            pairs = np.concatenate((first, arr))
        else:
            pairs = arr
        if pairs.size >= 2:
            a = pairs[:-1].astype(np.int64)
            b = pairs[1:].astype(np.int64)
            for i in range(a.size):
                self._pair_counts[a[i], b[i]] += 1
        self._prev_symbol = int(arr[-1])

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        mode = str(params.get("mode", "bytes"))
        downsample = int(params.get("downsample", 1))
        # reset and compute from scratch
        self._buf = bytearray(bts)
        self._count_bytes = len(bts)
        self._prev_symbol = None
        self._ensure_counts(mode)
        if mode == "bits":
            arr = np.unpackbits(np.frombuffer(bts, dtype=np.uint8)).astype(np.int64)
        else:
            arr = np.frombuffer(bts, dtype=np.uint8).astype(np.int64)
        self._single_counts.fill(0)
        self._pair_counts.fill(0)
        if arr.size > 0:
            self._process_array(arr, downsample)

        tr = self._compute_result(params)
        end = time.time()
        tr.time_ms = (end - self._start) * 1000.0
        tr.bytes_processed = len(bts)
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if self._start is None:
            self._start = time.time()
        self._buf.extend(chunk)
        self._count_bytes += len(chunk)
        mode = str(params.get("mode", "bytes"))
        downsample = int(params.get("downsample", 1))
        max_buf = int(params.get("max_buffer_bytes", 1 << 20))
        self._ensure_counts(mode)
        if len(self._buf) > max_buf:
            arr = np.frombuffer(self._buf, dtype=np.uint8)
            arr = arr[::2]
            self._buf = bytearray(arr.tobytes())
        if mode == "bits":
            arr = np.unpackbits(np.frombuffer(chunk, dtype=np.uint8)).astype(np.int64)
        else:
            arr = np.frombuffer(chunk, dtype=np.uint8).astype(np.int64)
        if arr.size > 0:
            self._process_array(arr, downsample)

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        tr = self._compute_result(params)
        tr.bytes_processed = self._count_bytes
        # reset state
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._single_counts = None
        self._pair_counts = None
        self._alphabet_size = None
        self._prev_symbol = None
        return tr

    def _compute_result(self, params: Dict[str, Any]) -> TestResult:
        name = params.get("name", "mutual_information")
        mode = str(params.get("mode", "bytes"))
        downsample = int(params.get("downsample", 1))
        total_pairs = int(self._pair_counts.sum())
        total_singles = int(self._single_counts.sum())
        if total_pairs == 0 or total_singles == 0:
            tr = TestResult(test_name=name, passed=False, p_value=None, category="information",
                            p_values={}, effect_sizes={}, flags=["empty_data"],
                            metrics={"mutual_information": None, "total_pairs": total_pairs, "total_singles": total_singles, "mode": mode})
            return tr

        p_x = self._single_counts / total_singles  # P(X)
        p_y = p_x  # for adjacency first-order marginal of successor equals symbol marginal
        p_xy = self._pair_counts / total_pairs

        # compute mutual information I(X;Y) = sum_x,y p(x,y) log2( p(x,y) / (p(x)p(y)) )
        mi = 0.0
        pmi_vals = []
        # vectorized approach using the probability arrays
        p_x_arr = p_x
        p_y_arr = p_y
        p_xy_arr = p_xy
        # elementwise compute only where p_xy > 0
        nz = p_xy_arr > 0
        # to compute p(x)p(y) for each (x,y) pair, form outer product
        denom = np.outer(p_x_arr, p_y_arr)
        # MI
        mi = float(np.sum(p_xy_arr[nz] * np.log2(p_xy_arr[nz] / denom[nz])))
        # PMI values (pointwise)
        pmi_matrix = np.full_like(p_xy_arr, np.nan, dtype=np.float64)
        valid = nz
        pmi_matrix[valid] = np.log2(p_xy_arr[valid] / denom[valid])
        pmi_vals = pmi_matrix[valid].tolist()
        pmi_min = float(np.min(pmi_vals)) if len(pmi_vals) > 0 else None
        pmi_median = float(np.median(pmi_vals)) if len(pmi_vals) > 0 else None
        pmi_max = float(np.max(pmi_vals)) if len(pmi_vals) > 0 else None

        metrics = {
            "mutual_information": float(mi),
            "pmi_min": pmi_min,
            "pmi_median": pmi_median,
            "pmi_max": pmi_max,
            "total_pairs": total_pairs,
            "total_singles": total_singles,
            "alphabet_size": int(self._alphabet_size),
            "mode": mode,
            "downsample": int(downsample),
        }

        tr = TestResult(test_name=name, passed=True, p_value=None, category="information", p_values={"mutual_information": float(mi)}, metrics=metrics)
        return tr
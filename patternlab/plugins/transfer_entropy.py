# -*- coding: utf-8 -*-
"""Transfer Entropy (first-order proxy) plugin.

This plugin computes a first-order transfer-entropy-like quantity by measuring
the mutual information between a symbol and its successor:

  TE(X->Y) ~= I(X_t ; Y_{t+1})

For a single stream, it's equivalent to mutual information between adjacent symbols.
Streaming-supported; accepts same params as mutual_information/conditional_entropy.

Parameters:
  - mode: "bytes" (default) or "bits"
  - downsample: integer >=1 (default 1)
  - max_buffer_bytes: memory cap for streaming (default 1<<20)
  - name: optional test name
"""

from typing import Dict, Any
import time
import numpy as np
from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class TransferEntropyTest(TestPlugin):
    """First-order transfer entropy proxy (I(X_t; X_{t+1}))"""

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._single_counts = None
        self._pair_counts = None
        self._alphabet_size = None
        self._prev_symbol = None

    def describe(self) -> str:
        return "Transfer Entropy proxy (I(X_t; X_{t+1})) - first-order adjacency"

    def _ensure_counts(self, mode: str):
        size = 2 if mode == "bits" else 256
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
        # reset
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._single_counts = None
        self._pair_counts = None
        self._alphabet_size = None
        self._prev_symbol = None
        return tr

    def _compute_result(self, params: Dict[str, Any]) -> TestResult:
        name = params.get("name", "transfer_entropy")
        total_pairs = int(self._pair_counts.sum())
        total_singles = int(self._single_counts.sum())
        mode = str(params.get("mode", "bytes"))
        if total_pairs == 0 or total_singles == 0:
            return TestResult(test_name=name, passed=False, p_value=None, category="information",
                              p_values={}, metrics={"transfer_entropy": None, "total_pairs": total_pairs, "total_singles": total_singles, "mode": mode})

        p_x = self._single_counts / total_singles
        p_xy = self._pair_counts / total_pairs
        denom = np.outer(p_x, p_x)  # approximation: marginal of successor ~ marginal of symbol
        nz = p_xy > 0
        te = float(np.sum(p_xy[nz] * np.log2(p_xy[nz] / denom[nz])))
        metrics = {"transfer_entropy": float(te), "total_pairs": total_pairs, "total_singles": total_singles, "alphabet_size": int(self._alphabet_size), "mode": mode}
        return TestResult(test_name=name, passed=True, p_value=None, category="information", p_values={"transfer_entropy": float(te)}, metrics=metrics)
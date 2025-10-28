# -*- coding: utf-8 -*-
"""Conditional entropy (H(Y|X)) plugin.

Streaming-supported TestPlugin that computes first-order conditional entropy
between adjacent symbols (bytes or bits). Uses numpy for efficient counting and
supports downsampling and a max_buffer_bytes limit for large streams.

Parameters accepted in params dict:
  - mode: "bytes" (default) or "bits"
  - downsample: integer >=1 (default 1)
  - max_buffer_bytes: memory cap (default 1<<20)
  - name: optional test name
"""

from typing import Dict, Any, Optional
import time
import math
import numpy as np

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView


class ConditionalEntropyTest(TestPlugin):
    """Compute H(Y|X) for first-order symbol sequences."""

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        # counts: single and pair counts; initialized lazily based on mode
        self._single_counts = None
        self._pair_counts = None
        self._alphabet_size = None
        self._prev_symbol = None

    def describe(self) -> str:
        return "Conditional entropy H(Y|X) (first-order) using bytes or bits"

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
        # update single counts
        vals, cnts = np.unique(arr, return_counts=True)
        self._single_counts[vals] += cnts
        # pairs
        if self._prev_symbol is not None:
            # account for pair across boundary
            first = np.array([self._prev_symbol], dtype=arr.dtype)
            pairs = np.concatenate((first, arr))
        else:
            pairs = arr
        if pairs.size >= 2:
            a = pairs[:-1].astype(np.int64)
            b = pairs[1:].astype(np.int64)
            # accumulate pair counts
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
        # downsample buffer if too large
        if len(self._buf) > max_buf:
            arr = np.frombuffer(self._buf, dtype=np.uint8)
            arr = arr[::2]
            self._buf = bytearray(arr.tobytes())
        # process chunk data
        if mode == "bits":
            arr = np.unpackbits(np.frombuffer(chunk, dtype=np.uint8)).astype(np.int64)
        else:
            arr = np.frombuffer(chunk, dtype=np.uint8).astype(np.int64)
        if arr.size > 0:
            self._process_array(arr, downsample)

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        # compute result from accumulated counts
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
        name = params.get("name", "conditional_entropy")
        mode = str(params.get("mode", "bytes"))
        downsample = int(params.get("downsample", 1))
        total_pairs = int(self._pair_counts.sum())
        total_singles = int(self._single_counts.sum())
        # handle empty input
        if total_pairs == 0 or total_singles == 0:
            tr = TestResult(test_name=name, passed=False, p_value=None, category="information",
                            p_values={}, effect_sizes={}, flags=["empty_data"],
                            metrics={"conditional_entropy": None, "joint_entropy": None, "marginal_entropy": None, "total_pairs": total_pairs, "total_singles": total_singles, "mode": mode})
            return tr
        # compute probabilities
        ps = self._single_counts / total_singles  # P(X)
        # P(Y|X) = pair_counts[x,y] / single_counts[x]
        cond_ent = 0.0
        joint_entropy = 0.0
        for x in range(self._alphabet_size):
            sx = self._single_counts[x]
            if sx == 0:
                continue
            row = self._pair_counts[x]
            py_given_x = row / sx
            # conditional entropy for this x
            nz = py_given_x > 0
            h_cond_x = -np.sum(py_given_x[nz] * np.log2(py_given_x[nz]))
            cond_ent += (sx / total_singles) * h_cond_x
            # joint entropy contribution
            pxy = row / total_pairs
            nzj = pxy > 0
            joint_entropy += -np.sum(pxy[nzj] * np.log2(pxy[nzj]))
        # marginal entropy H(Y) computed from singles of Y; for first-order symmetric case singles represent symbol frequencies
        marginal_entropy = -np.sum((self._single_counts / total_singles)[self._single_counts > 0] * np.log2((self._single_counts / total_singles)[self._single_counts > 0]))

        metrics = {
            "conditional_entropy": float(cond_ent),
            "joint_entropy": float(joint_entropy),
            "marginal_entropy": float(marginal_entropy),
            "total_pairs": total_pairs,
            "total_singles": total_singles,
            "alphabet_size": int(self._alphabet_size),
            "mode": mode,
            "downsample": int(downsample),
        }

        tr = TestResult(test_name=name, passed=True, p_value=None, category="information", p_values={"conditional_entropy": float(cond_ent)}, metrics=metrics)
        return tr
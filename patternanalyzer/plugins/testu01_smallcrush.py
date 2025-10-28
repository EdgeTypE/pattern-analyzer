# -*- coding: utf-8 -*-
"""Simplified TestU01 SmallCrush adapter plugin.

This adapter implements a subset of the SmallCrush battery suitable for
streaming and reasonably fast execution inside Pattern Analyzer. Implemented tests:
 - Monobit (bit frequency)
 - Runs (approximate runs distribution)
 - Collision (count of repeated 32-bit words / birthday-style collision)
Streaming supported via update()/finalize(). Results are returned as a single
TestResult with per-subtest p-values in `p_values` and metrics detailing counts.
"""

from typing import Dict, Any
import time
import numpy as np
from scipy import stats

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView


class SmallCrushAdapter(TestPlugin):
    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None

    def describe(self) -> str:
        return "TestU01 SmallCrush (subset) adapter"

    def _monobit_test(self, bits: np.ndarray) -> float:
        # bits is array of 0/1 values
        n = bits.size
        if n == 0:
            return None  # type: ignore
        s = bits.sum()
        # convert to +/-1
        z = (s - (n / 2.0)) / np.sqrt(n / 4.0)
        p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        return float(p)

    def _runs_test(self, bits: np.ndarray) -> float:
        n = bits.size
        if n == 0:
            return None  # type: ignore
        p_hat = bits.mean()
        if p_hat == 0 or p_hat == 1:
            return None  # no runs distribution
        # count runs
        runs = 1 + np.sum(bits[1:] != bits[:-1])
        # expected runs
        expected = 2.0 * n * p_hat * (1.0 - p_hat)
        var = 2.0 * n * p_hat * (1.0 - p_hat) * (2.0 * n * p_hat * (1.0 - p_hat) - 1) / float((n - 1)) if n > 1 else 1.0
        # approximate z
        z = (runs - expected) / np.sqrt(var) if var > 0 else 0.0
        p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        return float(p)

    def _collision_test(self, words: np.ndarray) -> float:
        n = words.size
        if n == 0:
            return None  # type: ignore
        # count collisions: number of duplicate words
        unique, counts = np.unique(words, return_counts=True)
        collisions = int(np.sum(counts - 1))
        # approximate using Poisson with lambda = n - unique
        lam = float(n - unique.size)
        # use Poisson survival for observed collisions
        p = 1.0 - stats.poisson.cdf(collisions - 1, lam) if lam >= 0 else None
        return float(p) if p is not None else None

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        downsample = int(params.get("downsample", 1))
        max_words = int(params.get("max_words", 1 << 16))
        # Bit view
        try:
            bits = np.array(data.bit_view(), dtype=np.uint8)
        except Exception:
            bits = np.frombuffer(bts, dtype=np.uint8)
            # fallback: expand bytes to bits MSB-first
            bits = np.unpackbits(bits).astype(np.uint8)
        if downsample > 1:
            bits = bits[::downsample]
        # Words view
        if len(bts) >= 4:
            words = np.frombuffer(bts, dtype=np.uint32)
            if downsample > 1:
                words = words[::downsample]
            if words.size > max_words:
                words = words[:max_words]
        else:
            words = np.empty(0, dtype=np.uint32)

        monobit_p = self._monobit_test(bits)
        runs_p = self._runs_test(bits)
        collision_p = self._collision_test(words)

        end = time.time()
        pvals = {}
        if monobit_p is not None:
            pvals["monobit"] = monobit_p
        if runs_p is not None:
            pvals["runs"] = runs_p
        if collision_p is not None:
            pvals["collision"] = collision_p

        # combined 'passed' heuristic: all p-values above alpha (default 0.01)
        alpha = float(params.get("alpha", 0.01))
        passed = all((v is None) or (v >= alpha) for v in pvals.values())

        tr = TestResult(
            test_name=params.get("name", "testu01_smallcrush"),
            passed=passed,
            p_value=min([v for v in pvals.values()]) if len(pvals) > 0 else None,
            category="testu01",
            p_values=pvals,
            metrics={"bits": int(bits.size), "words": int(words.size), "collisions_estimate": int(max(0, (words.size - np.unique(words).size)))},
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
            # downsample buffer by keeping every other 32-bit word
            arr = np.frombuffer(self._buf, dtype=np.uint32)
            arr = arr[::2]
            self._buf = bytearray(arr.tobytes())

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        bv = BytesView(bts)
        tr = self.run(bv, params)
        # reset state
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        return tr
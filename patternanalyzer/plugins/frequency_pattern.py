"""Frequency & classical-cipher pattern detector.

Performs byte-frequency analysis and simple Index-of-Coincidence (IoC)-based
Vigenère/key-length detection. Supports batch (run) and streaming (update/finalize)
APIs using patternanalyzer.plugin_api.BytesView and returns patternanalyzer.plugin_api.TestResult.

Features:
 - byte histogram (optionally downsampled)
 - IoC computation
 - simple Vigenère key-length candidates via average IoC per bin
 - streaming support with bounded buffer and downsampling
"""
import time
from collections import Counter
from typing import Dict, Any, Optional, List

try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore


class FrequencyPattern(TestPlugin):
    def describe(self) -> str:
        return "Byte-frequency analysis and simple classical-cipher pattern detection (IoC / Vigenere-like)"

    def __init__(self):
        self._buffer = bytearray()
        self._bytes_seen = 0
        self.stream_max_buffer = 1024 * 1024  # 1 MiB
        self.default_downsample = 1
        self.max_key_len = 16

    def _histogram(self, b: bytes, downsample: int = 1) -> Counter:
        if downsample <= 1:
            return Counter(b)
        # simple downsample by taking every Nth byte
        return Counter(b[i] for i in range(0, len(b), downsample))

    def _ioc(self, counts: Counter, total: int) -> float:
        if total <= 1:
            return 0.0
        # IoC = sum(f_i * (f_i - 1)) / (N * (N-1))
        num = sum(v * (v - 1) for v in counts.values())
        den = total * (total - 1)
        return float(num) / float(den) if den else 0.0

    def _vigenere_keylen_candidates(self, b: bytes, max_key: int = 16, downsample: int = 1) -> List[Dict[str, Any]]:
        N = len(b)
        if N < 2:
            return []
        candidates = []
        for keylen in range(1, min(max_key, N) + 1):
            # split into bins
            iocs = []
            for offset in range(keylen):
                chunk = bytes(b[offset::keylen])
                if downsample > 1:
                    chunk = bytes(chunk[i::downsample] for i in (0,))  # keep as bytes (no-op) 
                    # above line preserves chunk (explicit no-op to be clear); we won't downsample per-bin here to keep bins meaningful
                    chunk = chunk  # type: ignore
                c = Counter(chunk)
                iocs.append(self._ioc(c, len(chunk)))
            avg_ioc = sum(iocs) / len(iocs) if iocs else 0.0
            candidates.append({"keylen": keylen, "avg_ioc": avg_ioc})
        # sort by avg_ioc desc for reporting
        candidates.sort(key=lambda x: x["avg_ioc"], reverse=True)
        return candidates

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        start = time.perf_counter()
        downsample = int(params.get("downsample", self.default_downsample))
        max_key = int(params.get("max_key_len", self.max_key_len))
        vigenere_ioc_threshold = float(params.get("vigenere_ioc_threshold", 0.04))

        b = data.to_bytes()
        total = len(b)
        hist = self._histogram(b, downsample=downsample)
        ioc = self._ioc(hist, sum(hist.values()))
        key_candidates = self._vigenere_keylen_candidates(b, max_key=max_key, downsample=downsample)

        # Decide if likely classical substitution / polyalphabetic cipher present
        vigenere_like = any(c["avg_ioc"] >= vigenere_ioc_threshold for c in key_candidates[:5])

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        metrics = {
            "total_bytes": total,
            "histogram_top": hist.most_common(10),
            "ioc": ioc,
            "vigenere_keylen_candidates": key_candidates[:8],
        }
        flags = []
        if vigenere_like:
            flags.append("vigenere_like")
        tr = TestResult(
            test_name=params.get("name", "frequency_pattern"),
            passed=not vigenere_like,
            p_value=None,
            category="crypto",
            metrics=metrics,
            flags=flags,
            evidence=None,
            time_ms=elapsed_ms,
            bytes_processed=total,
        )
        if vigenere_like:
            tr.evidence = f"High average IoC for candidate key lengths: {[c for c in key_candidates[:3]]}"
        return tr

    # Streaming API
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        self._bytes_seen += len(chunk)
        self._buffer.extend(chunk)
        if len(self._buffer) > self.stream_max_buffer:
            # keep tail to preserve patterns
            self._buffer = self._buffer[-self.stream_max_buffer:]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bv = BytesView(bytes(self._buffer))
        tr = self.run(bv, params)
        tr.bytes_processed = int(self._bytes_seen)
        return tr
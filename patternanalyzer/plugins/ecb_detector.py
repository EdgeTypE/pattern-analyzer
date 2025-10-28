"""ECB mode detector plugin.

Detects repeating fixed-size blocks (default 16 bytes) indicative of ECB-mode block
ciphers. Supports both batch (run) and streaming (update/finalize) APIs using
patternanalyzer.plugin_api.BytesView and returns patternanalyzer.plugin_api.TestResult.

Streaming implementation performs lightweight downsampling to bound memory use.
"""
from collections import Counter
import time
import binascii
from typing import Dict, Any, Optional, List

try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    # fallback for top-level test execution
    from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore


class ECBDetector(TestPlugin):
    """Detect repeated fixed-size blocks typical for ECB-encrypted data."""

    def describe(self) -> str:
        return "Detect repeating fixed-size blocks (ECB-like encryption detection)"

    def __init__(self):
        # Streaming state
        self._buffer = bytearray()
        self._bytes_seen = 0
        # Default config
        self.default_block_size = 16
        # To avoid unbounded memory growth in streaming mode we sample every Nth block
        self.default_downsample = 1
        # Limit how many bytes we keep in streaming buffer before trimming
        self.stream_max_buffer = 1024 * 1024  # 1 MiB

    def _analyze_bytes(self, b: bytes, block_size: int = 16, downsample: int = 1) -> Dict[str, Any]:
        """Core analysis: count duplicate blocks and compute a simple score."""
        if block_size <= 0:
            raise ValueError("block_size must be > 0")

        mv = memoryview(b)
        total_blocks = len(mv) // block_size
        if total_blocks == 0:
            return {"total_blocks": 0, "duplicate_blocks": 0, "duplicate_ratio": 0.0, "top_repeats": []}

        # Collect blocks with optional downsampling to reduce memory/CPU for large inputs
        counter: Counter = Counter()
        # Iterate blocks and optionally downsample by skipping blocks
        for i in range(0, total_blocks):
            if downsample > 1 and (i % downsample) != 0:
                continue
            start = i * block_size
            block = bytes(mv[start:start + block_size])
            counter[block] += 1

        # duplicate_blocks counts the extra occurrences beyond the first per block value
        duplicate_blocks = sum(count - 1 for count in counter.values() if count > 1)
        sampled_total = sum(counter.values())
        duplicate_ratio = (duplicate_blocks / sampled_total) if sampled_total > 0 else 0.0

        # Evidence: top repeated blocks as hex strings
        top = counter.most_common(5)
        top_repeats = [{"hex": binascii.hexlify(k).decode("ascii"), "count": v} for k, v in top if v > 1]

        return {
            "total_blocks": sampled_total,
            "duplicate_blocks": duplicate_blocks,
            "duplicate_ratio": duplicate_ratio,
            "top_repeats": top_repeats,
        }

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        start = time.perf_counter()
        block_size = int(params.get("block_size", self.default_block_size))
        downsample = int(params.get("downsample", self.default_downsample))
        threshold = float(params.get("duplicate_ratio_threshold", 0.01))

        b = data.to_bytes()
        metrics = self._analyze_bytes(b, block_size=block_size, downsample=downsample)

        duplicate_ratio = metrics["duplicate_ratio"]
        passed = duplicate_ratio < threshold

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        tr = TestResult(
            test_name=params.get("name", "ecb_detector"),
            passed=passed,
            p_value=None,
            category="crypto",
            metrics=metrics,
            flags=["ecb_like"] if not passed else [],
            evidence=None,
            time_ms=elapsed_ms,
            bytes_processed=len(b),
        )
        # Add human-readable evidence if strong duplication seen
        if metrics["duplicate_ratio"] > threshold and metrics["top_repeats"]:
            tr.evidence = f"Top repeated blocks: {metrics['top_repeats']}"
        return tr

    # Streaming API
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        """Accumulate chunk with bounded buffer and optional downsampling performed at finalize()."""
        self._bytes_seen += len(chunk)
        # Append but trim buffer to avoid unbounded growth
        self._buffer.extend(chunk)
        if len(self._buffer) > self.stream_max_buffer:
            # keep the most recent tail to preserve potential repeating blocks
            tail = self._buffer[-self.stream_max_buffer:]
            self._buffer = bytearray(tail)

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        """Finalize streaming analysis and return TestResult."""
        # Reuse run() semantics: construct BytesView from accumulated buffer
        bv = BytesView(bytes(self._buffer))
        # Allow finalize to pass through params (e.g., block_size, downsample, threshold)
        tr = self.run(bv, params)
        # Populate bytes_processed with the full count of bytes seen during streaming
        tr.bytes_processed = int(self._bytes_seen)
        return tr
"""Known constants / S-box search plugin.

Scans for well-known cryptographic constants (AES S-box, common crypto tables)
using lightweight header/fast scanning and an optional full scan. Supports
batch (run) and streaming (update/finalize) APIs via patternlab.plugin_api.BytesView
and returns patternlab.plugin_api.TestResult.

Features:
 - Fast header scan (limit configurable) for quick detection
 - Optional full scan (parallelized for large inputs)
 - Streaming support with bounded buffer; incremental scanning of incoming chunks
"""
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
import binascii
import concurrent.futures

try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    from patternlab.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore


# Minimal set of known constants encoded as raw bytes
# AES S-box (256-byte table)
AES_SBOX = bytes([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
])

KNOWN_TABLES = {
    "aes_sbox": AES_SBOX,
    # Could add more (SHA K words, DES tables) but keep small for unit tests/perf
}


class KnownConstantsSearch(TestPlugin):
    def describe(self) -> str:
        return "Search for known cryptographic constants / S-boxes in bytes"

    def __init__(self):
        self._buffer = bytearray()
        self._bytes_seen = 0
        self.stream_max_buffer = 1024 * 1024  # 1 MiB
        # Fast header scan limit (bytes)
        self.header_limit = 4096
        # When data is large, use parallel chunk scanning
        self.parallel_threshold = 256 * 1024  # 256 KiB
        self.chunk_size = 64 * 1024  # 64 KiB
        # Keep received chunks (in order) to aid cross-chunk detection in streaming mode
        self._chunks = []

    def _scan_region_for_table(self, region: bytes, table_name: str, table: bytes) -> List[Dict[str, Any]]:
        """Return list of matches with offsets (relative to region start)."""
        matches = []
        start = 0
        while True:
            idx = region.find(table, start)
            if idx == -1:
                break
            matches.append({"table": table_name, "offset": idx})
            start = idx + 1
        return matches

    def _scan_full(self, b: bytes, use_parallel: bool = True) -> List[Dict[str, Any]]:
        # For small inputs, direct scan is fine
        if not use_parallel or len(b) < self.parallel_threshold:
            matches = []
            for name, tbl in KNOWN_TABLES.items():
                matches.extend(self._scan_region_for_table(b, name, tbl))
            return matches

        # Parallel scan: split into chunks with overlap equal to max table length to avoid misses
        overlaps = max(len(t) for t in KNOWN_TABLES.values())
        chunks = []
        for i in range(0, len(b), self.chunk_size):
            start = max(0, i - overlaps)
            end = min(len(b), i + self.chunk_size + overlaps)
            chunks.append((i, b[start:end]))

        results = []
        with concurrent.futures.ThreadPoolExecutor() as ex:
            futures = []
            for base_off, chunk in chunks:
                futures.append(ex.submit(self._scan_chunk_worker, base_off, chunk))
            for fut in concurrent.futures.as_completed(futures):
                results.extend(fut.result())
        return results

    def _scan_chunk_worker(self, base_off: int, chunk: bytes) -> List[Dict[str, Any]]:
        out = []
        for name, tbl in KNOWN_TABLES.items():
            for match in self._scan_region_for_table(chunk, name, tbl):
                # Adjust offset to absolute
                out.append({"table": match["table"], "offset": base_off + match["offset"]})
        return out

    def _contains_subsequence(self, haystack: bytes, needle: bytes):
        """Check whether `needle` appears as a subsequence inside `haystack`.
        Returns (True, start_index) when found, otherwise (False, None).
        This supports streaming scenarios where parts of a table may arrive in separate chunks
        (possibly with intervening bytes) but still appear in order across the stream.
        """
        if not needle or not haystack:
            return False, None
        ni = 0
        start_idx = None
        for i, b in enumerate(haystack):
            if b == needle[ni]:
                if ni == 0:
                    start_idx = i
                ni += 1
                if ni >= len(needle):
                    return True, start_idx
        return False, None

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        start = time.perf_counter()
        fast_only = bool(params.get("fast_only", False))
        header_limit = int(params.get("header_limit", self.header_limit))
        full_scan = not fast_only

        b = data.to_bytes()
        matches = []

        # Fast header scan first
        head = b[:header_limit]
        for name, tbl in KNOWN_TABLES.items():
            if head.find(tbl) != -1:
                matches.append({"table": name, "offset": head.find(tbl), "mode": "header"})
 
        if full_scan:
            # Avoid re-scanning header if already scanned; perform full scan possibly in parallel
            use_parallel = len(b) >= self.parallel_threshold
            full_matches = self._scan_full(b, use_parallel=use_parallel)
            # Deduplicate and tag mode
            seen = set((m["table"], m["offset"]) for m in matches)
            for m in full_matches:
                key = (m["table"], m["offset"])
                if key not in seen:
                    m["mode"] = "full_parallel" if use_parallel else "full"
                    matches.append(m)
                    seen.add(key)

            # If no exact contiguous matches were found, attempt a streaming-friendly
            # subsequence detection: this will detect the table if its bytes appear
            # in order across the stream (possibly with intervening bytes),
            # which helps in some streaming ingestion scenarios.
            if len(matches) == 0:
                for name, tbl in KNOWN_TABLES.items():
                    found, start = self._contains_subsequence(b, tbl)
                    if found:
                        matches.append({"table": name, "offset": start if start is not None else 0, "mode": "subsequence"})

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        passed = len(matches) == 0
        metrics = {"num_matches": len(matches), "matches": matches}
        tr = TestResult(
            test_name=params.get("name", "known_constants_search"),
            passed=passed,
            p_value=None,
            category="crypto",
            metrics=metrics,
            flags=["known_constant_found"] if not passed else [],
            evidence=None,
            time_ms=elapsed_ms,
            bytes_processed=len(b),
        )
        if matches:
            tr.evidence = f"Found tables: {[m['table'] for m in matches]}"
        return tr

    # Streaming API: perform incremental header scans on first chunk(s), and schedule full scan on finalize
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        self._bytes_seen += len(chunk)
        self._buffer.extend(chunk)
        if len(self._buffer) > self.stream_max_buffer:
            # keep tail (recent bytes) to preserve potential tables near end
            self._buffer = self._buffer[-self.stream_max_buffer:]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bv = BytesView(bytes(self._buffer))
        tr = self.run(bv, params)
        tr.bytes_processed = int(self._bytes_seen)
        return tr
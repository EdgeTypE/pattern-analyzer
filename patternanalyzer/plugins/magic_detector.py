from typing import Optional, Dict, Any
from patternanalyzer.plugin_api import TestPlugin, BytesView, TestResult

# Lightweight magic-number detector plugin.
# - Uses a small built-in signatures table for common formats (PNG, PDF, ZIP, JPG, GIF)
# - Supports streaming via update()/finalize() by accumulating a small header buffer
# - Returns TestResult with category="format" and metrics describing detection


class MagicDetector(TestPlugin):
    """Detect file type by magic numbers (header bytes). Lightweight and streaming-capable."""

    def describe(self) -> str:
        return "Detects common file formats using magic-number signatures (PNG, PDF, ZIP, JPG, GIF)."

    # Built-in signatures: mapping name -> bytes prefix
    _SIGNATURES = {
        "png": b"\x89PNG\r\n\x1a\n",
        "pdf": b"%PDF-",
        "zip": b"PK\x03\x04",
        "zip_central": b"PK\x01\x02",
        "jpeg": b"\xFF\xD8\xFF",
        "gif87a": b"GIF87a",
        "gif89a": b"GIF89a",
    }

    def __init__(self, header_limit: int = 4096):
        # header_limit: how many leading bytes we keep for detection
        self.header_limit = int(header_limit)
        self._buf = bytearray()
        self._total_len = 0

    def _detect_from_bytes(self, data: bytes) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        for name, sig in self._SIGNATURES.items():
            if data.startswith(sig):
                # normalize some names
                if name.startswith("gif"):
                    friendly = "gif"
                elif name.startswith("zip"):
                    friendly = "zip"
                else:
                    friendly = name
                return {"detected": friendly, "signature": sig.hex(), "confidence": 0.95, "matched_name": name}
        # fallback heuristics
        if data[:4] == b"\x50\x4B\x05\x06":  # empty zip archive end of central dir
            return {"detected": "zip", "signature": data[:4].hex(), "confidence": 0.8, "matched_name": "zip_eocd"}
        return None

    # Single-call API
    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        # accept params override for header_limit
        limit = int(params.get("header_limit", self.header_limit))
        head = bytes(data.data[:limit])
        detected = self._detect_from_bytes(head)
        metrics = {"header_len": len(head)}
        if detected:
            metrics.update(detected)
            return TestResult(test_name="magic_detector", passed=True, p_value=None, category="format", metrics=metrics)
        else:
            # unknown format
            metrics["detected"] = None
            return TestResult(test_name="magic_detector", passed=False, p_value=None, category="format", metrics=metrics)

    # Streaming API: collect only a bounded header (first N bytes) and track total length
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if chunk is None:
            return
        self._total_len += len(chunk)
        if len(self._buf) < self.header_limit:
            need = self.header_limit - len(self._buf)
            self._buf.extend(chunk[:need])

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        head = bytes(self._buf)
        detected = self._detect_from_bytes(head)
        metrics = {"header_len": len(head), "total_bytes_seen": self._total_len}
        if detected:
            metrics.update(detected)
            return TestResult(test_name="magic_detector", passed=True, p_value=None, category="format", metrics=metrics)
        metrics["detected"] = None
        return TestResult(test_name="magic_detector", passed=False, p_value=None, category="format", metrics=metrics)
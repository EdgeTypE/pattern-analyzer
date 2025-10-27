from typing import Dict, Any, Optional
from patternlab.plugin_api import TestPlugin, BytesView, TestResult

class PDFStructure(TestPlugin):
    """PDF structure analyzer (lightweight, header-only).

    - Detects PDF by %PDF- signature
    - Counts occurrences of 'obj' and '%EOF' in the header snapshot
    - Attempts to find the /Type /Page token to estimate page presence
    - Streaming-capable: accumulates bounded header and tracks total bytes seen
    """

    def describe(self) -> str:
        return "Lightweight PDF structure analysis: detects PDF, counts objects, EOF markers and hints for pages."

    def __init__(self, header_limit: int = 65536):
        self.header_limit = int(header_limit)
        self._buf = bytearray()
        self._total_len = 0

    def _analyze_buf(self, buf: bytes) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "is_pdf": False,
            "obj_count": 0,
            "eof_count": 0,
            "page_hint": False,
            "parsed_bytes": len(buf),
        }
        if not buf:
            return out
        if not buf.startswith(b"%PDF-"):
            # quick heuristic: may still be PDF if signature not in snapshot
            if b"%PDF-" not in buf:
                return out
            out["is_pdf"] = True
        else:
            out["is_pdf"] = True

        # Count occurrences of ' obj' or '\nobj' token (object headers)
        try:
            # Simple byte-pattern counting avoids heavy parsing
            out["obj_count"] = buf.count(b"\nobj") + buf.count(b" obj")
            out["eof_count"] = buf.count(b"%EOF")
            # page hint: presence of '/Type /Page' or '/Page' token
            if b"/Type /Page" in buf or b"/Page" in buf:
                out["page_hint"] = True
        except Exception:
            out.setdefault("warnings", []).append("count_error")
        return out

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit))
        snap = bytes(data.data[:limit])
        parsed = self._analyze_buf(snap)
        metrics = {
            "header_limit": limit,
            "parsed_bytes": parsed.get("parsed_bytes"),
            "is_pdf": parsed.get("is_pdf", False),
            "obj_count": parsed.get("obj_count", 0),
            "eof_count": parsed.get("eof_count", 0),
            "page_hint": parsed.get("page_hint", False),
        }
        if parsed.get("is_pdf"):
            return TestResult(test_name="pdf_structure", passed=True, p_value=None, category="format", metrics=metrics)
        return TestResult(test_name="pdf_structure", passed=False, p_value=None, category="format", metrics=metrics)

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if chunk is None:
            return
        self._total_len += len(chunk)
        if len(self._buf) < self.header_limit:
            need = self.header_limit - len(self._buf)
            self._buf.extend(chunk[:need])

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit)) if isinstance(params, dict) else self.header_limit
        snap = bytes(self._buf[:limit])
        parsed = self._analyze_buf(snap)
        metrics = {
            "header_limit": limit,
            "parsed_bytes": parsed.get("parsed_bytes"),
            "is_pdf": parsed.get("is_pdf", False),
            "obj_count": parsed.get("obj_count", 0),
            "eof_count": parsed.get("eof_count", 0),
            "page_hint": parsed.get("page_hint", False),
            "total_bytes_seen": self._total_len,
        }
        if parsed.get("is_pdf"):
            return TestResult(test_name="pdf_structure", passed=True, p_value=None, category="format", metrics=metrics)
        return TestResult(test_name="pdf_structure", passed=False, p_value=None, category="format", metrics=metrics)
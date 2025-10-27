from typing import Dict, Any, List, Optional
from patternlab.plugin_api import TestPlugin, BytesView, TestResult
import struct
import io
import binascii

class PNGStructure(TestPlugin):
    """PNG chunk-structure analyzer.
    
    - Detects PNG by signature
    - Parses chunk headers (type + length) up to a configurable header_limit or chunk limit
    - Extracts IHDR fields and summarizes IDAT total size
    - Supports streaming via update()/finalize() by buffering only the leading bytes
    """

    def describe(self) -> str:
        return "Analyses PNG chunk structure (IHDR, IDAT sizes, chunk sequence)."

    def __init__(self, header_limit: int = 65536, max_chunks: int = 200):
        self.header_limit = int(header_limit)
        self.max_chunks = int(max_chunks)
        self._buf = bytearray()
        self._total_len = 0

    def _parse_buffer(self, buf: bytes) -> Dict[str, Any]:
        out: Dict[str, Any] = {"is_png": False, "chunks": [], "ihdr": None, "idat_total": 0, "parsed_bytes": 0}
        if len(buf) < 8:
            out["parsed_bytes"] = len(buf)
            return out
        sig = buf[:8]
        if sig != b"\x89PNG\r\n\x1a\n":
            out["parsed_bytes"] = min(len(buf), 8)
            return out
        out["is_png"] = True
        f = io.BytesIO(buf[8:])
        parsed = 8
        chunks: List[Dict[str, Any]] = []
        idat_total = 0
        try:
            for i in range(self.max_chunks):
                # need at least 12 bytes for length(4)+type(4)+crc(4)
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                length = struct.unpack(">I", hdr[:4])[0]
                ctype = hdr[4:8].decode("ascii", errors="replace")
                # read chunk data (may be truncated in header-only mode)
                data = f.read(length)
                crc = f.read(4)
                parsed += 8 + len(data) + len(crc)
                chunks.append({"type": ctype, "length": len(data)})
                if ctype == "IHDR" and len(data) >= 13:
                    try:
                        width, height, bit_depth, color_type, comp, filt, inter = struct.unpack(">IIBBBBB", data[:13])
                        out["ihdr"] = {
                            "width": int(width),
                            "height": int(height),
                            "bit_depth": int(bit_depth),
                            "color_type": int(color_type),
                            "compression": int(comp),
                            "filter": int(filt),
                            "interlace": int(inter),
                        }
                    except Exception:
                        out.setdefault("warnings", []).append("failed_parse_ihdr")
                if ctype == "IDAT":
                    idat_total += len(data)
                if ctype == "IEND":
                    break
                # Stop if we've consumed more than header_limit bytes from original buffer
                if parsed >= self.header_limit:
                    break
        except Exception:
            out.setdefault("warnings", []).append("parse_error")
        out["chunks"] = chunks
        out["idat_total"] = idat_total
        out["parsed_bytes"] = parsed
        return out

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit))
        max_chunks = int(params.get("max_chunks", self.max_chunks))
        # create local parser state without mutating instance (run is stateless)
        hb = bytes(data.data[:limit])
        self_max_chunks = self.max_chunks
        try:
            self.max_chunks = max_chunks
            parsed = self._parse_buffer(hb)
        finally:
            self.max_chunks = self_max_chunks
        metrics: Dict[str, Any] = {
            "header_limit": limit,
            "parsed_bytes": parsed.get("parsed_bytes"),
            "is_png": parsed.get("is_png", False),
            "chunk_count": len(parsed.get("chunks", [])),
            "idat_total": parsed.get("idat_total", 0),
            "ihdr": parsed.get("ihdr"),
        }
        if parsed.get("is_png"):
            return TestResult(test_name="png_structure", passed=True, p_value=None, category="format", metrics=metrics)
        else:
            return TestResult(test_name="png_structure", passed=False, p_value=None, category="format", metrics=metrics)

    # Streaming API: accumulate bounded header and track total length
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if chunk is None:
            return
        self._total_len += len(chunk)
        if len(self._buf) < self.header_limit:
            need = self.header_limit - len(self._buf)
            self._buf.extend(chunk[:need])

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit)) if isinstance(params, dict) else self.header_limit
        max_chunks = int(params.get("max_chunks", self.max_chunks)) if isinstance(params, dict) else self.max_chunks
        # Temporarily set parser limits then restore
        self_max_chunks = self.max_chunks
        self_header_limit = self.header_limit
        try:
            self.max_chunks = max_chunks
            self.header_limit = limit
            parsed = self._parse_buffer(bytes(self._buf))
        finally:
            self.max_chunks = self_max_chunks
            self.header_limit = self_header_limit
        metrics: Dict[str, Any] = {
            "header_limit": limit,
            "parsed_bytes": parsed.get("parsed_bytes"),
            "is_png": parsed.get("is_png", False),
            "chunk_count": len(parsed.get("chunks", [])),
            "idat_total": parsed.get("idat_total", 0),
            "ihdr": parsed.get("ihdr"),
            "total_bytes_seen": self._total_len,
        }
        if parsed.get("is_png"):
            return TestResult(test_name="png_structure", passed=True, p_value=None, category="format", metrics=metrics)
        return TestResult(test_name="png_structure", passed=False, p_value=None, category="format", metrics=metrics)
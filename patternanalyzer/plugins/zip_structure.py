from typing import Dict, Any, List, Optional
from patternanalyzer.plugin_api import TestPlugin, BytesView, TestResult
import struct
import io
import binascii

class ZIPStructure(TestPlugin):
    """ZIP structure analyzer.

    - Detects ZIP by local file header / central directory signatures
    - Parses local file headers and central directory entries when available within a bounded header snapshot
    - Reports per-entry compressed/uncompressed sizes and a simple compression ratio summary
    - Streaming-capable: accumulates a bounded head buffer and tracks total bytes seen
    """

    LFH_SIG = b"PK\x03\x04"
    CEN_SIG = b"PK\x01\x02"
    EOCD_SIG = b"PK\x05\x06"

    def __init__(self, header_limit: int = 65536, max_entries: int = 200):
        self.header_limit = int(header_limit)
        self.max_entries = int(max_entries)
        self._buf = bytearray()
        self._total_len = 0

    def describe(self) -> str:
        return "Analyses ZIP local headers / central directory entries and computes basic compression statistics."

    def _parse_local_headers(self, buf: bytes) -> Dict[str, Any]:
        out: Dict[str, Any] = {"is_zip": False, "entries": [], "parsed_bytes": 0, "warnings": []}
        if len(buf) < 4:
            out["parsed_bytes"] = len(buf)
            return out
        # quick magic check
        if self.LFH_SIG not in buf and self.CEN_SIG not in buf and self.EOCD_SIG not in buf:
            out["parsed_bytes"] = min(len(buf), 4)
            return out
        out["is_zip"] = True
        f = io.BytesIO(buf)
        parsed = 0
        entries: List[Dict[str, Any]] = []
        try:
            # scan for local file headers up to limit
            while True:
                chunk = f.read(4)
                if len(chunk) < 4:
                    break
                parsed += 4
                if chunk != self.LFH_SIG:
                    # Seek forward to next possible signature byte-wise (best-effort)
                    f.seek(-3, io.SEEK_CUR)
                    parsed -= 3
                    b = f.read(1)
                    if not b:
                        break
                    parsed += 1
                    continue
                # read fixed 26 bytes following signature for local file header
                hdr = f.read(26)
                if len(hdr) < 26:
                    out.setdefault("warnings", []).append("truncated_local_header")
                    break
                parsed += len(hdr)
                (version, flags, compression, mod_time, mod_date, crc32, comp_size, uncomp_size, fname_len, extra_len) = struct.unpack("<HHHHHIIIHH", hdr)
                fname = f.read(fname_len)
                extra = f.read(extra_len)
                parsed += fname_len + extra_len
                try:
                    name = fname.decode("utf-8", errors="replace")
                except Exception:
                    name = fname.hex()
                entries.append({
                    "name": name,
                    "compression": int(compression),
                    "crc32": hex(crc32),
                    "compressed_size": int(comp_size),
                    "uncompressed_size": int(uncomp_size),
                })
                if len(entries) >= self.max_entries:
                    out.setdefault("warnings", []).append("max_entries_reached")
                    break
        except Exception:
            out.setdefault("warnings", []).append("parse_error")
        out["entries"] = entries
        out["parsed_bytes"] = parsed
        return out

    def _parse_central_dir(self, buf: bytes) -> Dict[str, Any]:
        """Try to parse central directory entries if present in the snapshot."""
        out: Dict[str, Any] = {"central_found": False, "entries": [], "parsed_bytes": 0, "warnings": []}
        if len(buf) < 22:
            out["parsed_bytes"] = len(buf)
            return out
        idx = buf.find(self.CEN_SIG)
        if idx == -1:
            out["parsed_bytes"] = len(buf)
            return out
        out["central_found"] = True
        f = io.BytesIO(buf[idx:])
        parsed = 0
        entries: List[Dict[str, Any]] = []
        try:
            while True:
                sig = f.read(4)
                if len(sig) < 4:
                    break
                parsed += 4
                if sig != self.CEN_SIG:
                    break
                hdr = f.read(42)
                if len(hdr) < 42:
                    out.setdefault("warnings", []).append("truncated_central_header")
                    break
                parsed += len(hdr)
                (vers_made, vers_needed, flags, comp, mod_time, mod_date, crc32, comp_size, uncomp_size, fname_len, extra_len, comment_len, disk_start, int_attr, ext_attr, lfh_offset) = struct.unpack("<HHHHHHIIIHHHIIiI", hdr)
                fname = f.read(fname_len)
                extra = f.read(extra_len)
                comment = f.read(comment_len)
                parsed += fname_len + extra_len + comment_len
                try:
                    name = fname.decode("utf-8", errors="replace")
                except Exception:
                    name = fname.hex()
                entries.append({
                    "name": name,
                    "compression": int(comp),
                    "crc32": hex(crc32) if isinstance(crc32, int) else crc32,
                    "compressed_size": int(comp_size),
                    "uncompressed_size": int(uncomp_size),
                    "lfh_offset": int(lfh_offset),
                })
                if len(entries) >= self.max_entries:
                    out.setdefault("warnings", []).append("max_entries_reached")
                    break
        except Exception:
            out.setdefault("warnings", []).append("central_parse_error")
        out["entries"] = entries
        out["parsed_bytes"] = parsed
        return out

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit))
        max_entries = int(params.get("max_entries", self.max_entries))
        hb = bytes(data.data[:limit])
        # parse local headers and central dir
        c_parser = self._parse_central_dir(hb)
        l_parser = self._parse_local_headers(hb)
        entries = c_parser.get("entries") or l_parser.get("entries") or []
        total_comp = sum(e.get("compressed_size", 0) or 0 for e in entries)
        total_uncomp = sum(e.get("uncompressed_size", 0) or 0 for e in entries)
        comp_ratio = None
        if total_uncomp > 0:
            comp_ratio = float(total_comp) / float(total_uncomp)
        metrics: Dict[str, Any] = {
            "header_limit": limit,
            "parsed_bytes": max(c_parser.get("parsed_bytes", 0), l_parser.get("parsed_bytes", 0)),
            "is_zip": bool(entries),
            "entry_count": len(entries),
            "total_compressed": total_comp,
            "total_uncompressed": total_uncomp,
            "compression_ratio": comp_ratio,
            "central_dir_found": bool(c_parser.get("central_found")),
            "warnings": list(dict.fromkeys((c_parser.get("warnings") or []) + (l_parser.get("warnings") or []))),
        }
        # include up to first 20 entries as preview
        metrics["entries_preview"] = entries[:20]
        if metrics["is_zip"]:
            return TestResult(test_name="zip_structure", passed=True, p_value=None, category="format", metrics=metrics)
        return TestResult(test_name="zip_structure", passed=False, p_value=None, category="format", metrics=metrics)

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if chunk is None:
            return
        self._total_len += len(chunk)
        if len(self._buf) < self.header_limit:
            need = self.header_limit - len(self._buf)
            self._buf.extend(chunk[:need])

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        limit = int(params.get("header_limit", self.header_limit)) if isinstance(params, dict) else self.header_limit
        max_entries = int(params.get("max_entries", self.max_entries)) if isinstance(params, dict) else self.max_entries
        # parse buffer
        buf = bytes(self._buf[:limit])
        c_parser = self._parse_central_dir(buf)
        l_parser = self._parse_local_headers(buf)
        entries = c_parser.get("entries") or l_parser.get("entries") or []
        total_comp = sum(e.get("compressed_size", 0) or 0 for e in entries)
        total_uncomp = sum(e.get("uncompressed_size", 0) or 0 for e in entries)
        comp_ratio = None
        if total_uncomp > 0:
            comp_ratio = float(total_comp) / float(total_uncomp)
        metrics = {
            "header_limit": limit,
            "parsed_bytes": max(c_parser.get("parsed_bytes", 0), l_parser.get("parsed_bytes", 0)),
            "is_zip": bool(entries),
            "entry_count": len(entries),
            "total_compressed": total_comp,
            "total_uncompressed": total_uncomp,
            "compression_ratio": comp_ratio,
            "central_dir_found": bool(c_parser.get("central_found")),
            "total_bytes_seen": self._total_len,
            "warnings": list(dict.fromkeys((c_parser.get("warnings") or []) + (l_parser.get("warnings") or []))),
            "entries_preview": entries[:20],
        }
        if metrics["is_zip"]:
            return TestResult(test_name="zip_structure", passed=True, p_value=None, category="format", metrics=metrics)
        return TestResult(test_name="zip_structure", passed=False, p_value=None, category="format", metrics=metrics)
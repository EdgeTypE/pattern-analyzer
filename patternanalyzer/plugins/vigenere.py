from __future__ import annotations
from typing import Dict, Any, Optional
from patternanalyzer.plugin_api import BytesView, TransformPlugin

class VigenerePlugin(TransformPlugin):
    """
    Basit Vigenère tarzı transform plugin'i.
    Params:
      - key: bytes or str
      - mode: 'enc' veya 'dec' (default 'enc')
    Not: demo amaçlı; küçük veri için güvenli değil.
    """
    def describe(self) -> Dict[str,Any]:
        return {
            "name": "vigenere",
            "version": "0.1",
            "params": {
                "key": {"type": "bytes", "min_len": 1},
                "mode": {"type": "str", "enum": ["enc", "dec"], "default": "enc"}
            }
        }

    def run(self, b: BytesView, params: Dict[str, Any]) -> BytesView:
        key = params.get("key", b"KEY")
        if isinstance(key, str):
            key_bytes = key.encode()
        elif isinstance(key, (bytes, bytearray)):
            key_bytes = bytes(key)
        else:
            raise TypeError("key must be bytes or str")
 
        mode = params.get("mode", "enc")
        # Use BytesView API to obtain bytes (compatible with plugin_api.BytesView)
        data = b.to_bytes()
        out = bytearray(len(data))
        klen = len(key_bytes)
        for i, x in enumerate(data):
            k = key_bytes[i % klen]
            if mode == "enc":
                out[i] = (x + k) & 0xFF
            else:
                out[i] = (x - k) & 0xFF
        return BytesView(memoryview(bytes(out)))
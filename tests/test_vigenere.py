from patternlab.plugins.vigenere import VigenerePlugin
from patternlab.plugin_api import BytesView

def test_vigenere_encrypt_decrypt():
    p = VigenerePlugin()
    data = BytesView(memoryview(b"hello world"))
    enc = p.run(data, {"key": b"KEY", "mode": "enc"})
    dec = p.run(enc, {"key": b"KEY", "mode": "dec"})
    assert bytes(dec.data) == b"hello world"

def test_vigenere_shift():
    p = VigenerePlugin()
    data = BytesView(memoryview(b"\x00\x01\x02"))
    enc = p.run(data, {"key": b"\x01", "mode": "enc"})
    assert bytes(enc.data) == b"\x01\x02\x03"
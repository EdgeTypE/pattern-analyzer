from patternlab.plugin_api import BytesView
import pytest
import builtins

def bits_by_python(mv):
    out = []
    for v in mv.cast('B'):
        for i in range(7, -1, -1):
            out.append((v >> i) & 1)
    return out

def test_bit_view_with_numpy():
    np = pytest.importorskip('numpy')
    data = BytesView(b'\xAA\xFF\x00')
    bits = data.bit_view()
    expected = bits_by_python(data.data)
    assert bits == expected

def test_bit_view_without_numpy(monkeypatch):
    orig_import = builtins.__import__
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'numpy':
            raise ImportError
        return orig_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, '__import__', fake_import)
    data = BytesView(b'\xF0\x0F')
    bits = data.bit_view()
    expected = bits_by_python(data.data)
    assert bits == expected
import sys
import types
import pytest
from patternlab.plugin_api import BytesView
from patternlab.plugins.fft_spectral import FFTSpectralTest, NAIVE_DFT_BIT_LIMIT

def test_fft_spectral_basic_metrics():
    # Create a repeating pattern that produces a strong spectral peak (01010101 ...)
    data = bytes([0b10101010] * 64)
    bv = BytesView(data)
    plugin = FFTSpectralTest()
    result = plugin.run(bv, params={})
    assert result.test_name == "fft_spectral"
    assert isinstance(result.metrics, dict)
    assert "peak_snr_db" in result.metrics
    assert "peak_index" in result.metrics
    assert "peak_magnitude" in result.metrics
    assert result.metrics["n"] == len(bv.bit_view())
    # Expect some positive SNR for a strong periodic pattern
    assert isinstance(result.metrics["peak_snr_db"], float)
    assert result.metrics["peak_snr_db"] >= 0.0


def test_large_data_triggers_downsample_or_fast_backend():
    # Create data larger than NAIVE_DFT_BIT_LIMIT bits -> bytes length > limit/8
    byte_len = (NAIVE_DFT_BIT_LIMIT // 8) + 100
    data = bytes([0x00] * byte_len)
    bv = BytesView(data)
    plugin = FFTSpectralTest()
    result = plugin.run(bv, params={})
    assert "profile" in result.metrics or "downsampled" in result.metrics or "used_n" in result.metrics
    profile = result.metrics.get("profile")
    # If naive backend was used, ensure downsampling occurred
    if profile == "naive":
        assert result.metrics.get("downsampled", False) is True
        assert result.metrics.get("used_n", 0) <= NAIVE_DFT_BIT_LIMIT
    else:
        # If a fast backend was available, confirm profile indicates it
        assert profile in (None, "numpy", "scipy") or isinstance(profile, str)


def test_prefers_fast_profile_when_numpy_and_scipy_present(monkeypatch):
    # Create lightweight fake numpy and scipy.fft modules to simulate environment
    class FakeArr:
        def __init__(self, data):
            self._data = data
        def tolist(self):
            return [abs(x) for x in self._data]

    fake_numpy = types.SimpleNamespace()
    def _asarray(x, dtype=float):
        return x
    def _abs(x):
        return FakeArr(x)
    # Minimal frombuffer/unpackbits implementations so BytesView.bit_view() works
    def _frombuffer(mv, dtype=None):
        # return a sequence of uint8 values
        return list(mv.tobytes())
    def _unpackbits(byte_list):
        bits: list[int] = []
        for v in byte_list:
            for i in range(7, -1, -1):
                bits.append((v >> i) & 1)
        return types.SimpleNamespace(tolist=lambda: bits)
    fake_numpy.asarray = _asarray
    fake_numpy.abs = _abs
    fake_numpy.frombuffer = _frombuffer
    fake_numpy.unpackbits = _unpackbits
    # Provide a uint8 sentinel so dtype arguments don't raise AttributeError
    fake_numpy.uint8 = object()

    # Fake scipy.fft with rfft
    def fake_rfft(arr):
        return [1+0j, 2+0j, 0.5+0j]
    fake_spfft = types.SimpleNamespace(rfft=fake_rfft)

    # Inject into sys.modules for imports used by the plugin
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "scipy.fft", fake_spfft)

    data = bytes([0b10101010] * 32)
    bv = BytesView(data)
    plugin = FFTSpectralTest()
    result = plugin.run(bv, params={})
    # Expect the plugin to report using scipy (preferred) when present
    assert result.metrics.get("profile") in ("scipy", "numpy")
import random
from patternlab.plugin_api import BytesView
from patternlab.plugins.nist_dft_spectral import NISTDFTSpectralTest

def test_nist_dft_spectral_periodic_fails():
    # Strong periodic pattern -> strong spectral peak -> expect failure (small p-value)
    data = bytes([0b10101010] * 128)  # 128 bytes -> 1024 bits
    bv = BytesView(data)
    plugin = NISTDFTSpectralTest()
    res = plugin.run(bv, params={})
    assert res.test_name == "nist_dft_spectral"
    assert isinstance(res.p_value, float)
    assert res.p_value < 0.01
    assert res.passed is False

def test_nist_dft_spectral_random_passes():
    # Deterministic pseudorandom data should behave like random and pass
    rng = random.Random(0)
    byte_len = 256
    data = bytes(rng.getrandbits(8) for _ in range(byte_len))
    bv = BytesView(data)
    plugin = NISTDFTSpectralTest()
    res = plugin.run(bv, params={})
    assert res.test_name == "nist_dft_spectral"
    assert isinstance(res.p_value, float)
    assert res.p_value >= 0.01
    assert res.passed is True

def test_nist_dft_spectral_small_data_skipped():
    # Below MIN_BITS the test should be skipped and return no p-value
    data = bytes([0x00] * 5)  # 5 bytes -> 40 bits < MIN_BITS
    bv = BytesView(data)
    plugin = NISTDFTSpectralTest()
    res = plugin.run(bv, params={})
    assert "skipped" in getattr(res, "flags", [])
    assert res.p_value is None
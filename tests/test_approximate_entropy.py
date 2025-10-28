import random

from patternanalyzer.plugins.approximate_entropy import ApproximateEntropyTest
from patternanalyzer.plugin_api import BytesView, TestResult


def bits_to_bytes(bits):
    """Pack list of bits (0/1) MSB-first per byte into bytes object."""
    # pad to full bytes
    pad = (-len(bits)) % 8
    bits = bits + [0] * pad
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | (1 if b else 0)
        out.append(byte)
    return bytes(out)


def test_approximate_entropy_regular_vs_random():
    # Regular sequence: repeating '01' pattern (low complexity)
    N = 1024
    regular_bits = [0 if i % 2 == 0 else 1 for i in range(N)]

    # Random sequence (deterministic seed)
    random.seed(0)
    random_bits = [random.getrandbits(1) for _ in range(N)]

    reg_bytes = bits_to_bytes(regular_bits)
    rnd_bytes = bits_to_bytes(random_bits)

    reg_view = BytesView(reg_bytes)
    rnd_view = BytesView(rnd_bytes)

    plugin = ApproximateEntropyTest()

    params = {"m": 2, "min_templates": 16, "alpha": 0.01}

    res_reg = plugin.run(reg_view, params)
    res_rnd = plugin.run(rnd_view, params)

    assert isinstance(res_reg, TestResult)
    assert isinstance(res_rnd, TestResult)

    # both should expose ap_en metric and valid p_value
    assert "ap_en" in res_reg.metrics
    assert "ap_en" in res_rnd.metrics
    assert 0.0 <= res_reg.p_value <= 1.0
    assert 0.0 <= res_rnd.p_value <= 1.0

    # Random sequence should have higher approximate entropy than the simple repeating pattern
    assert res_rnd.metrics["ap_en"] >= res_reg.metrics["ap_en"]


def test_approximate_entropy_skipped_for_small_input():
    # Small input that does not provide enough templates for m and m+1
    N = 10
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = ApproximateEntropyTest()
    params = {"m": 4, "min_templates": 16, "alpha": 0.01}

    res = plugin.run(view, params)

    # Expect a skipped dict describing insufficient data
    assert isinstance(res, dict)
    assert res.get("status") == "skipped"
    assert "insufficient data" in res.get("reason", "")
import random

from patternlab.plugins.non_overlapping_template_matching import NonOverlappingTemplateMatching
from patternlab.plugin_api import BytesView, TestResult

def bits_to_bytes(bits):
    """Pack list of bits (0/1) MSB-first per byte into bytes object."""
    pad = (-len(bits)) % 8
    bits = bits + [0] * pad
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | (1 if b else 0)
        out.append(byte)
    return bytes(out)


def test_non_overlapping_all_zeros_fails():
    # All zeros should contain many non-overlapping matches of "00000000"
    N = 512
    bits = [0] * N
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = NonOverlappingTemplateMatching()
    params = {"template": "00000000", "min_bits": 256, "alpha": 0.01}

    res = plugin.run(view, params)
    assert isinstance(res, TestResult)
    assert res.test_name == "non_overlapping_template_matching"
    assert 0.0 <= res.p_value <= 1.0
    # Expect test to fail (very unlikely to be random)
    assert res.passed is False
    assert res.metrics["observed_count"] >= 1
    assert res.metrics["total_bits"] == N


def test_non_overlapping_alternating_passes():
    # Alternating pattern '01' has low chance of containing 8 zeros in a row
    N = 512
    bits = [0 if i % 2 == 0 else 1 for i in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = NonOverlappingTemplateMatching()
    params = {"template": "00000000", "min_bits": 256, "alpha": 0.01}

    res = plugin.run(view, params)
    assert isinstance(res, TestResult)
    assert res.test_name == "non_overlapping_template_matching"
    assert 0.0 <= res.p_value <= 1.0
    # Should pass since template rarely occurs
    assert res.passed is True
    assert res.metrics["observed_count"] == 0
    assert res.metrics["total_bits"] == N


def test_non_overlapping_skipped_for_small_input():
    # Small input should be skipped due to min_bits requirement
    N = 100
    random.seed(0)
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = NonOverlappingTemplateMatching()
    params = {"template": "00000000", "min_bits": 256, "alpha": 0.01}

    res = plugin.run(view, params)
    assert isinstance(res, dict)
    assert res.get("status") == "skipped"
    assert "insufficient data" in res.get("reason", "")
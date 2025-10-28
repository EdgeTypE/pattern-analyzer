import random
import pytest

from patternanalyzer.plugins.maurers_universal import MaurersUniversalTest
from patternanalyzer.plugin_api import BytesView, TestResult


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


def test_maurers_universal_regular_vs_random():
    # Use a reasonably large N so there are many non-overlapping blocks
    N = 1024
    # Regular low-entropy sequence: repeating '01'
    regular_bits = [0 if i % 2 == 0 else 1 for i in range(N)]

    # Random sequence (deterministic seed)
    random.seed(0)
    random_bits = [random.getrandbits(1) for _ in range(N)]

    reg_bytes = bits_to_bytes(regular_bits)
    rnd_bytes = bits_to_bytes(random_bits)

    reg_view = BytesView(reg_bytes)
    rnd_view = BytesView(rnd_bytes)

    plugin = MaurersUniversalTest()

    # Use small Q/min_blocks in tests so we can run the test with limited input
    params = {"L": 6, "Q": 10, "min_blocks": 20, "alpha": 0.01}

    res_reg = plugin.run(reg_view, params)
    res_rnd = plugin.run(rnd_view, params)

    assert isinstance(res_reg, TestResult)
    assert isinstance(res_rnd, TestResult)

    # both should expose fn metric and valid p_value
    assert "fn" in res_reg.metrics
    assert "fn" in res_rnd.metrics
    assert 0.0 <= res_reg.p_value <= 1.0
    assert 0.0 <= res_rnd.p_value <= 1.0

    # Random sequence should have higher average log-distance (fn) than a trivial repeating pattern
    assert res_rnd.metrics["fn"] >= res_reg.metrics["fn"]


def test_maurers_universal_skipped_for_small_input():
    # Small input that doesn't produce enough non-overlapping blocks
    N = 60  # with L=6 this yields 10 blocks
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = MaurersUniversalTest()
    # Force a large min_blocks to trigger the skipped path
    params = {"L": 6, "min_blocks": 100, "alpha": 0.01}

    res = plugin.run(view, params)

    # Expect a skipped dict describing insufficient data
    assert isinstance(res, dict)
    assert res.get("status") == "skipped"
    assert "insufficient data" in res.get("reason", "")


def test_maurers_universal_invalid_L_raises_value_error():
    # Prepare a small valid buffer
    N = 192
    random.seed(1)
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = MaurersUniversalTest()

    # L too small should raise ValueError
    with pytest.raises(ValueError):
        plugin.run(view, {"L": 3})

    # Non-integer L should raise ValueError
    with pytest.raises(ValueError):
        plugin.run(view, {"L": "not-an-int"})
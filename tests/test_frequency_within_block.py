import random
import pytest
from patternanalyzer.plugins.frequency_within_block import FrequencyWithinBlockTest
from patternanalyzer.plugin_api import BytesView, TestResult

def bits_to_bytes(bits):
    pad = (-len(bits)) % 8
    bits = bits + [0] * pad
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | (1 if b else 0)
        out.append(byte)
    return bytes(out)

def test_frequency_within_block_batch_and_pvalue_range():
    N = 1024
    random.seed(0)
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = FrequencyWithinBlockTest()
    params = {"block_size": 16, "alpha": 0.01}
    res = plugin.run(view, params)
    assert isinstance(res, TestResult)
    assert 0.0 <= res.p_value <= 1.0
    assert res.metrics["block_size"] == 16
    assert res.metrics["block_count"] == (N // 16)

def test_frequency_within_block_streaming_matches_batch():
    N = 1024
    random.seed(1)
    bits = [random.getrandbits(1) for _ in range(N)]
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = FrequencyWithinBlockTest()
    params = {"block_size": 32, "alpha": 0.01}
    batch = plugin.run(view, params)
    # streaming: feed bytes in small chunks
    splugin = FrequencyWithinBlockTest()
    chunk_size = 20
    for i in range(0, len(b), chunk_size):
        splugin.update(b[i:i+chunk_size], params)
    sres = splugin.finalize(params)
    assert isinstance(sres, TestResult)
    # p-values should match (within floating tolerance)
    assert abs(batch.p_value - sres.p_value) < 1e-8 or (batch.p_value == sres.p_value)

def test_frequency_within_block_invalid_block_size_raises():
    N = 128
    bits = [0] * N
    b = bits_to_bytes(bits)
    view = BytesView(b)
    plugin = FrequencyWithinBlockTest()
    with pytest.raises(ValueError):
        plugin.run(view, {"block_size": 0})
    # streaming invalid block size
    s = FrequencyWithinBlockTest()
    with pytest.raises(ValueError):
        s.update(b, {"block_size": 0})
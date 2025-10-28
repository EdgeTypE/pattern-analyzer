import os
from patternanalyzer.plugin_api import BytesView
from patternanalyzer.plugins.lz_complexity import LZComplexityTest

def test_lz_complexity_low_for_repeated():
    # Highly repetitive data should yield a low normalized complexity score
    data = b"A" * 4096
    bv = BytesView(data)
    plugin = LZComplexityTest()
    result = plugin.run(bv, params={"preview_len": len(data)})
    assert result.test_name == "lz_complexity"
    score = result.metrics["score"]
    assert score < 0.05

def test_lz_complexity_high_for_random():
    # Random data (os.urandom) should yield a relatively high complexity score
    data = os.urandom(4096)
    bv = BytesView(data)
    plugin = LZComplexityTest()
    result = plugin.run(bv, params={"preview_len": len(data)})
    score = result.metrics["score"]
    assert score > 0.25
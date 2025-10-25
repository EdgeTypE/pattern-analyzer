import pytest
from patternlab.plugin_api import BytesView
from patternlab.plugins.linear_complexity import LinearComplexityTest

def test_linear_complexity_simple():
    # sequence of alternating bits has low linear complexity relative to length
    data = bytes([0b10101010] * 32)
    bv = BytesView(data)
    plugin = LinearComplexityTest()
    result = plugin.run(bv, params={})
    assert result.test_name == "linear_complexity"
    assert "linear_complexity" in result.metrics
    L = result.metrics["linear_complexity"]
    assert isinstance(L, int)
    # Complexity should be at least 1 and no more than n
    n = result.metrics["n"]
    assert 1 <= L <= n
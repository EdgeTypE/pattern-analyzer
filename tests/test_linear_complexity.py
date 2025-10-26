import pytest
from patternlab.plugin_api import BytesView, TestResult
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

def test_linear_complexity_empty_input_returns_error_metric_and_none_pvalue():
    bv = BytesView(b"")
    plugin = LinearComplexityTest()
    res = plugin.run(bv, params={})
    assert isinstance(res, TestResult)
    # Implementation returns an error metric and None p_value for empty input
    assert res.metrics.get("error") == "no data"
    assert res.p_value is None
    assert res.passed is False

def test_linear_complexity_does_not_support_streaming_api():
    plugin = LinearComplexityTest()
    # Plugin should not expose streaming update/finalize methods
    assert not hasattr(plugin, "update")
    assert not hasattr(plugin, "finalize")
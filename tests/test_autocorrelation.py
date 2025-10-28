import pytest
from patternanalyzer.plugin_api import BytesView
from patternanalyzer.plugins.autocorrelation import AutocorrelationTest

def test_autocorrelation_basic():
    # Construct a periodic bit pattern (01010101...) which should show strong lag-1 correlation
    data = bytes([0b10101010] * 64)
    bv = BytesView(data)
    plugin = AutocorrelationTest()
    # request a small lag window
    result = plugin.run(bv, params={"lag_max": 8})
    assert result.test_name == "autocorrelation"
    metrics = result.metrics
    assert "autocorr" in metrics and "lags" in metrics and "n" in metrics
    autocorr = metrics["autocorr"]
    lags = metrics["lags"]
    assert isinstance(autocorr, list)
    assert isinstance(lags, list)
    assert len(autocorr) == len(lags)
    assert len(autocorr) == metrics["lag_max"] + 1
    # autocorr[0] should be normalized to 1.0
    assert abs(autocorr[0] - 1.0) < 1e-9
    # Correlations should be within [-1, 1]
    for v in autocorr:
        assert -1.0 - 1e-9 <= v <= 1.0 + 1e-9
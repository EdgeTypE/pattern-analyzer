"""Tests for Cumulative Sums (Cusum) test plugin."""

import pytest
from patternanalyzer.plugins.cusum import CumulativeSumsTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestCumulativeSums:
    def setup_method(self):
        self.plugin = CumulativeSumsTest()

    def test_describe(self):
        desc = self.plugin.describe()
        assert isinstance(desc, str) and len(desc) > 0

    def test_insufficient_bits(self):
        # default min_bits is 100, so short input should be considered insufficient
        data = BytesView(b'\x00')  # 8 bits
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "cusum"
        assert result.p_value == 1.0
        # ensure both directional p-values are present and 1.0 for insufficient data
        assert "cusum_forward" in result.p_values and "cusum_backward" in result.p_values
        assert result.p_values["cusum_forward"] == 1.0
        assert result.p_values["cusum_backward"] == 1.0
        assert result.metrics.get("reason") == "insufficient_bits"
        assert result.metrics["total_bits"] == 8

    def test_all_zeros_unbalanced(self):
        # 16 bytes = 128 bits, large enough for default min_bits
        data = BytesView(b'\x00' * 16)
        result = self.plugin.run(data, {"min_bits": 100})
        assert isinstance(result, TestResult)
        assert result.test_name == "cusum"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bits"] == 128
        # directional p-values reported
        assert "cusum_forward" in result.p_values and "cusum_backward" in result.p_values
        p_fwd = result.p_values["cusum_forward"]
        p_bwd = result.p_values["cusum_backward"]
        # overall p_value should be the minimum of the two directional p-values
        assert result.p_value == pytest.approx(min(p_fwd, p_bwd))
        # all zeros should produce extreme cumulative deviation -> small p_value
        assert result.p_value < 0.05

    def test_balanced_pattern(self):
        # 0xAA pattern has roughly equal 0s and 1s
        data = BytesView(b'\xAA' * 16)
        result = self.plugin.run(data, {"min_bits": 100})
        assert isinstance(result, TestResult)
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bits"] == 128
        # directional p-values reported
        assert "cusum_forward" in result.p_values and "cusum_backward" in result.p_values
        p_fwd = result.p_values["cusum_forward"]
        p_bwd = result.p_values["cusum_backward"]
        # both directions should be non-extreme for balanced data
        assert p_fwd > 0.01
        assert p_bwd > 0.01
        # overall p_value should reflect the minimum of the two
        assert result.p_value == pytest.approx(min(p_fwd, p_bwd))
        assert result.p_value > 0.01
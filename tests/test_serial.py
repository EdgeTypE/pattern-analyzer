"""Unit tests for SerialTest plugin."""

import pytest
from patternlab.plugins.serial_test import SerialTest
from patternlab.plugin_api import BytesView, TestResult


class TestSerialTest:
    def setup_method(self):
        self.plugin = SerialTest()

    def test_empty_data(self):
        data = BytesView(b'')
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "serial"
        assert result.metrics["total_bits"] == 0
        assert result.passed is True

    def test_all_zeros_fails(self):
        # All zeros will create very imbalanced n-gram counts -> low p-values
        data = BytesView(b'\x00' * 8)
        result = self.plugin.run(data, {"max_m": 2, "alpha": 0.01})
        assert isinstance(result, TestResult)
        assert result.test_name == "serial"
        assert "m_1" in result.p_values and "m_2" in result.p_values
        assert 0.0 <= result.p_value <= 1.0
        # Expect at least one small p-value causing overall failure
        assert result.passed is False

    def test_alternating_pattern_passes(self):
        # 0xAA pattern (10101010) should be fairly uniform for short n-grams
        data = BytesView(b'\xAA' * 8)
        result = self.plugin.run(data, {"max_m": 2, "alpha": 0.01})
        assert isinstance(result, TestResult)
        assert result.test_name == "serial"
        assert "m_1" in result.p_values and "m_2" in result.p_values
        assert 0.0 <= result.p_value <= 1.0
        # Balanced alternating pattern expected to pass for small m
        assert result.passed is True or result.p_value > 0.001
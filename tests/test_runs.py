"""Unit tests for RunsTest plugin (Wald–Wolfowitz)."""

import pytest
from patternlab.plugins.runs_test import RunsTest
from patternlab.plugin_api import BytesView, TestResult


class TestRunsTest:
    def setup_method(self):
        self.plugin = RunsTest()

    def test_all_zeros(self):
        """All zeros should produce very few runs and likely fail the runs test."""
        data = BytesView(b'\x00' * 16)  # 128 bits
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "runs"
        assert 0.0 <= result.p_value <= 1.0
        assert "runs" in result.metrics
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones"] == 0
        assert result.metrics["zeros"] == 128
        assert result.metrics["runs"] == 1
        assert result.passed is False

    def test_alternating_pattern(self):
        """Alternating bits (0xAA) should have many runs and pass the test."""
        data = BytesView(b'\xAA' * 16)  # 10101010 pattern
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "runs"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones"] == 64
        assert result.metrics["zeros"] == 64
        # alternating pattern should produce many runs (close to n)
        assert result.metrics["runs"] > 1
        assert result.passed is True

    def test_min_bits_short_circuit(self):
        """If data is shorter than min_bits, the plugin should short-circuit and mark as passed."""
        data = BytesView(b'\x00')  # 8 bits < default min_bits=20
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "runs"
        assert result.metrics["total_bits"] == 8
        assert result.passed is True
        assert result.p_value == 1.0
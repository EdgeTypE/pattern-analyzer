"""Tests for Monobit test plugin."""

import pytest
import math
from patternanalyzer.plugins.monobit import MonobitTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestMonobitTest:
    """Test cases for MonobitTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = MonobitTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_all_zeros(self):
        """Test with all zeros (should fail monobit test)."""
        # Create 16 bytes of zeros = 128 bits
        data = BytesView(b'\x00' * 16)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert result.passed is False  # Should fail for all zeros
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones_count"] == 0

    def test_all_ones(self):
        """Test with all ones (should fail monobit test)."""
        # Create 16 bytes of 0xFF = 128 bits
        data = BytesView(b'\xFF' * 16)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert result.passed is False  # Should fail for all ones
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones_count"] == 128

    def test_balanced_bits(self):
        """Test with balanced 0s and 1s (should pass monobit test)."""
        # Create pattern with roughly equal 0s and 1s: 0xAA = 10101010
        # 16 bytes * 8 bits = 128 bits, should have ~64 ones
        data = BytesView(b'\xAA' * 16)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert result.passed is True  # Should pass for balanced data
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones_count"] == 64  # 0xAA pattern

    def test_alternating_pattern(self):
        """Test with alternating bits."""
        # 0xCC = 11001100 pattern
        data = BytesView(b'\xCC' * 16)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert result.passed is True
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 128
        assert result.metrics["ones_count"] == 64  # 0xCC pattern

    def test_small_data(self):
        """Test with small data."""
        data = BytesView(b'\xF0')  # 11110000 in binary
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 8
        assert result.metrics["ones_count"] == 4  # 0xF0 pattern

    def test_empty_data(self):
        """Test with empty data."""
        data = BytesView(b'')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "monobit"
        assert 0.0 <= result.p_value <= 1.0
        assert result.z_score is not None
        assert result.metrics is not None
        assert result.metrics["total_bits"] == 0
        assert result.metrics["ones_count"] == 0

    def test_p_value_range(self):
        """Test that p_value is always in valid range."""
        test_cases = [
            b'\x00' * 32,  # All zeros
            b'\xFF' * 32,  # All ones
            b'\xAA' * 32,  # Alternating
            b'\xCC' * 32,  # Another pattern
        ]

        for test_data in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {})

            assert 0.0 <= result.p_value <= 1.0, f"Invalid p_value: {result.p_value}"
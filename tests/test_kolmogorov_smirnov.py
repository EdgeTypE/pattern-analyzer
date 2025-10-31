"""Tests for Kolmogorov-Smirnov test plugin."""

import pytest
from patternanalyzer.plugins.kolmogorov_smirnov import KolmogorovSmirnovTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestKolmogorovSmirnovTest:
    """Test cases for KolmogorovSmirnovTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = KolmogorovSmirnovTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_empty_data(self):
        """Test with empty data."""
        data = BytesView(b'')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.passed is True
        assert result.p_value == 1.0
        assert result.metrics["total_bytes"] == 0

    def test_uniform_distribution(self):
        """Test with uniformly distributed data."""
        # Create data with each byte value appearing equally
        data_bytes = bytearray()
        for i in range(256):
            data_bytes.extend([i] * 100)
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.passed is True
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value > 0.1  # Should have high p-value for uniform data
        assert result.metrics["total_bytes"] == 25600

    def test_biased_distribution(self):
        """Test with highly biased data."""
        # Create data with all same byte value
        data = BytesView(b'\x00' * 1000)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.passed is False
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value < 0.01
        assert result.metrics["total_bytes"] == 1000

    def test_skewed_distribution(self):
        """Test with skewed distribution."""
        # Create data skewed towards lower byte values
        data_bytes = bytearray()
        for i in range(128):
            data_bytes.extend([i] * 10)
        for i in range(128, 256):
            data_bytes.extend([i] * 2)
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 1536

    def test_small_sample(self):
        """Test with small data sample."""
        data = BytesView(b'\x00\x01\x02\x03\x04')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 5

    def test_sequential_data(self):
        """Test with sequential byte values."""
        data = BytesView(bytes(range(256)))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 256

    def test_custom_alpha(self):
        """Test with custom alpha parameter."""
        data = BytesView(b'\xFF' * 1000)
        params = {"alpha": 0.05}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert result.passed is False
        assert result.p_value < 0.05

    def test_ks_statistic_range(self):
        """Test that K-S statistic is in valid range [0, 1]."""
        test_cases = [
            b'\x00' * 500,
            b'\xFF' * 500,
            bytes(range(256)) * 4,
            bytes([i % 256 for i in range(1000)]),
        ]

        for test_data in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {})
            assert 0.0 <= result.metrics["ks_statistic"] <= 1.0

    def test_p_value_range(self):
        """Test that p_value is always in valid range."""
        test_cases = [
            b'\x00' * 500,
            b'\xFF' * 500,
            bytes(range(256)) * 4,
            bytes([i % 256 for i in range(1000)]),
        ]

        for test_data in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {})
            assert 0.0 <= result.p_value <= 1.0, f"Invalid p_value: {result.p_value}"

    def test_max_deviation_equals_statistic(self):
        """Test that max_deviation equals ks_statistic."""
        data = BytesView(bytes(range(256)) * 10)
        result = self.plugin.run(data, {})
        
        assert result.metrics["max_deviation"] == result.metrics["ks_statistic"]

    def test_repeated_values(self):
        """Test with repeated byte values."""
        # Create data with multiple occurrences of same values
        data = BytesView(b'\x10\x20\x30' * 100)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "kolmogorov_smirnov"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 300

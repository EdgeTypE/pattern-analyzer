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

    def test_ascending_sequence(self):
        """Test with strictly ascending byte sequence."""
        data = BytesView(bytes(range(256)))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 256

    def test_descending_sequence(self):
        """Test with strictly descending byte sequence."""
        data = BytesView(bytes(range(255, -1, -1)))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 256

    def test_very_large_sample(self):
        """Test K-S with very large sample."""
        data_bytes = bytearray()
        for _ in range(500):
            data_bytes.extend(bytes(range(256)))
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.metrics["total_bytes"] == 128000
        assert 0.0 <= result.p_value <= 1.0

    def test_single_value_repeated(self):
        """Test with single value repeated many times."""
        data = BytesView(b'\x80' * 1000)
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.passed is False
        assert result.p_value < 0.01

    def test_category_and_p_values(self):
        """Test that category and p_values are set correctly."""
        data = BytesView(bytes(range(256)) * 5)
        result = self.plugin.run(data, {})
        
        assert result.category == "statistical"
        assert "kolmogorov_smirnov" in result.p_values
        assert result.p_values["kolmogorov_smirnov"] == result.p_value

    def test_ks_statistic_zero_for_perfect_uniform(self):
        """Test that perfect uniform distribution has very low K-S statistic."""
        data_bytes = bytearray()
        for i in range(256):
            data_bytes.extend([i] * 100)
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        # For perfect uniform, K-S statistic should be very small
        assert result.metrics["ks_statistic"] < 0.01

    def test_two_byte_values(self):
        """Test with only two different byte values."""
        data = BytesView(b'\x00\xFF' * 500)
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.passed is False
        assert result.metrics["total_bytes"] == 1000

    def test_metrics_completeness(self):
        """Test that all expected metrics are present."""
        data = BytesView(bytes(range(100)))
        result = self.plugin.run(data, {})
        
        expected_metrics = ["total_bytes", "ks_statistic", "max_deviation"]
        for metric in expected_metrics:
            assert metric in result.metrics

    def test_lower_half_bytes_only(self):
        """Test with only lower half of byte range (0-127)."""
        data = BytesView(bytes(range(128)) * 10)
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.passed is False  # Should fail as not uniform over full range
        assert 0.0 <= result.p_value <= 1.0

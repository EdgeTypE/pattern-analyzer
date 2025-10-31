"""Tests for Chi-Square test plugin."""

import pytest
from patternanalyzer.plugins.chi_square import ChiSquareTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestChiSquareTest:
    """Test cases for ChiSquareTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = ChiSquareTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "chi" in desc.lower() or "square" in desc.lower()

    def test_empty_data(self):
        """Test with empty data."""
        data = BytesView(b'')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is True
        assert result.p_value == 1.0
        assert result.metrics["total_bytes"] == 0

    def test_uniform_distribution(self):
        """Test with uniformly distributed data."""
        # Create data with each byte value appearing roughly equally
        data_bytes = bytearray()
        for i in range(256):
            data_bytes.extend([i] * 100)  # Each byte value appears 100 times
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is True  # Should pass for uniform distribution
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value > 0.1  # Should have high p-value for uniform data
        assert result.metrics["total_bytes"] == 25600
        assert result.metrics["unique_bytes"] == 256

    def test_biased_distribution(self):
        """Test with highly biased data (all same byte)."""
        # Create data with all zeros
        data = BytesView(b'\x00' * 1000)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is False  # Should fail for biased data
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value < 0.01  # Should have very low p-value
        assert result.metrics["total_bytes"] == 1000
        assert result.metrics["unique_bytes"] == 1

    def test_moderately_biased_distribution(self):
        """Test with moderately biased data."""
        # Create data with some bytes appearing more frequently
        data_bytes = bytearray()
        data_bytes.extend([0] * 500)  # Byte 0 appears 500 times
        data_bytes.extend([1] * 300)  # Byte 1 appears 300 times
        for i in range(2, 102):
            data_bytes.extend([i] * 2)  # Other bytes appear less frequently
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 1000
        assert result.metrics["unique_bytes"] == 102

    def test_small_sample(self):
        """Test with small data sample."""
        data = BytesView(b'\x00\x01\x02\x03\x04')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 5

    def test_streaming_matches_batch(self):
        """Test that streaming mode produces same result as batch mode."""
        # Create test data
        data_bytes = bytearray()
        for i in range(256):
            data_bytes.extend([i] * 50)
        
        # Batch mode
        batch_plugin = ChiSquareTest()
        data = BytesView(bytes(data_bytes))
        batch_result = batch_plugin.run(data, {})

        # Streaming mode
        stream_plugin = ChiSquareTest()
        chunk_size = 1000
        for i in range(0, len(data_bytes), chunk_size):
            chunk = bytes(data_bytes[i:i + chunk_size])
            stream_plugin.update(chunk, {})
        stream_result = stream_plugin.finalize({})

        # Results should be identical
        assert batch_result.passed == stream_result.passed
        assert abs(batch_result.p_value - stream_result.p_value) < 1e-10
        assert batch_result.metrics["total_bytes"] == stream_result.metrics["total_bytes"]
        assert abs(batch_result.metrics["chi_square_statistic"] - 
                   stream_result.metrics["chi_square_statistic"]) < 1e-10

    def test_custom_alpha(self):
        """Test with custom alpha parameter."""
        # Create biased data
        data = BytesView(b'\xFF' * 1000)
        params = {"alpha": 0.05}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is False
        assert result.p_value < 0.05

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

    def test_chi_square_statistic_positive(self):
        """Test that chi-square statistic is always non-negative."""
        test_cases = [
            b'\x00' * 100,
            bytes(range(256)),
            bytes([i % 10 for i in range(1000)]),
        ]

        for test_data in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {})
            assert result.metrics["chi_square_statistic"] >= 0.0

    def test_degrees_of_freedom(self):
        """Test that degrees of freedom is always 255."""
        data = BytesView(bytes(range(256)) * 10)
        result = self.plugin.run(data, {})
        assert result.metrics["degrees_of_freedom"] == 255

    def test_very_large_data(self):
        """Test with very large data sample."""
        # Create 100KB of uniform data
        data_bytes = bytearray()
        for _ in range(400):
            data_bytes.extend(bytes(range(256)))
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is True
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 102400

    def test_single_byte(self):
        """Test with single byte of data."""
        data = BytesView(b'\xFF')
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bytes"] == 1

    def test_two_values_only(self):
        """Test with data containing only two different byte values."""
        data = BytesView(b'\x00\xFF' * 500)
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert result.passed is False
        assert result.metrics["unique_bytes"] == 2
        assert result.metrics["total_bytes"] == 1000

    def test_streaming_empty_chunks(self):
        """Test streaming with some empty chunks."""
        stream_plugin = ChiSquareTest()
        
        stream_plugin.update(b'', {})
        stream_plugin.update(bytes(range(256)), {})
        stream_plugin.update(b'', {})
        stream_plugin.update(bytes(range(256)), {})
        
        result = stream_plugin.finalize({})
        
        assert isinstance(result, TestResult)
        assert result.metrics["total_bytes"] == 512

    def test_streaming_single_byte_chunks(self):
        """Test streaming with very small chunks."""
        stream_plugin = ChiSquareTest()
        
        for i in range(256):
            for _ in range(10):
                stream_plugin.update(bytes([i]), {})
        
        result = stream_plugin.finalize({})
        
        assert isinstance(result, TestResult)
        assert result.passed is True
        assert result.metrics["total_bytes"] == 2560

    def test_multiple_finalize_calls(self):
        """Test that multiple finalize calls reset state."""
        stream_plugin = ChiSquareTest()
        
        # First run
        stream_plugin.update(bytes(range(256)), {})
        result1 = stream_plugin.finalize({})
        
        # Second run should start fresh
        stream_plugin.update(b'\x00' * 1000, {})
        result2 = stream_plugin.finalize({})
        
        assert result1.metrics["total_bytes"] == 256
        assert result2.metrics["total_bytes"] == 1000
        assert result1.passed != result2.passed

    def test_category_field(self):
        """Test that category is correctly set."""
        data = BytesView(bytes(range(100)))
        result = self.plugin.run(data, {})
        assert result.category == "statistical"

    def test_p_values_dict(self):
        """Test that p_values dictionary is populated."""
        data = BytesView(bytes(range(256)) * 10)
        result = self.plugin.run(data, {})
        assert "chi_square" in result.p_values
        assert result.p_values["chi_square"] == result.p_value

    def test_metrics_completeness(self):
        """Test that all expected metrics are present."""
        data = BytesView(bytes(range(256)) * 10)
        result = self.plugin.run(data, {})
        
        expected_metrics = ["total_bytes", "chi_square_statistic", 
                           "degrees_of_freedom", "unique_bytes"]
        for metric in expected_metrics:
            assert metric in result.metrics

    def test_near_uniform_distribution(self):
        """Test with near-uniform but slightly skewed distribution."""
        data_bytes = bytearray()
        for i in range(256):
            count = 100 + (i % 3)  # Slight variation
            data_bytes.extend([i] * count)
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.test_name == "chi_square"
        assert 0.0 <= result.p_value <= 1.0

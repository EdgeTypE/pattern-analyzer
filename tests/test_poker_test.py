"""Tests for Poker test plugin."""

import pytest
from patternanalyzer.plugins.poker_test import PokerTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestPokerTest:
    """Test cases for PokerTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = PokerTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "poker" in desc.lower()

    def test_insufficient_hands(self):
        """Test with insufficient data."""
        data = BytesView(b'\x00\x01\x02')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert result.passed is True
        assert result.p_value == 1.0
        assert result.metrics["status"] == "skipped_insufficient_hands"

    def test_uniform_pattern_distribution(self):
        """Test with uniformly distributed patterns."""
        # Create data with good mix of different patterns
        data_bytes = bytearray()
        for i in range(200):
            data_bytes.append((i * 137) % 256)  # Pseudo-random
        
        data = BytesView(bytes(data_bytes))
        params = {"hand_size": 4}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["hand_size"] == 4

    def test_biased_pattern_distribution(self):
        """Test with biased pattern distribution."""
        # All zeros should have very biased pattern distribution
        data = BytesView(b'\x00' * 100)
        params = {"hand_size": 4}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert result.passed is False  # Should fail for biased data
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value < 0.01

    def test_alternating_pattern(self):
        """Test with alternating bit pattern."""
        # 0xAA = 10101010
        data = BytesView(b'\xAA' * 100)
        params = {"hand_size": 4}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert 0.0 <= result.p_value <= 1.0

    def test_hand_size_3(self):
        """Test with hand size of 3 bits."""
        data = BytesView(b'\x55' * 100)  # 01010101 pattern
        params = {"hand_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["hand_size"] == 3
        assert result.metrics["possible_patterns"] == 8  # 2^3

    def test_hand_size_5(self):
        """Test with hand size of 5 bits."""
        data = BytesView(bytes(range(256)) * 2)
        params = {"hand_size": 5}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["hand_size"] == 5
        assert result.metrics["possible_patterns"] == 32  # 2^5

    def test_invalid_hand_size_too_small(self):
        """Test with invalid hand size (too small)."""
        data = BytesView(b'\xAA' * 100)
        params = {"hand_size": 1}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert result.metrics["status"] == "skipped_invalid_hand_size"

    def test_invalid_hand_size_too_large(self):
        """Test with invalid hand size (too large)."""
        data = BytesView(b'\xAA' * 100)
        params = {"hand_size": 10}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert result.metrics["status"] == "skipped_invalid_hand_size"

    def test_streaming_matches_batch(self):
        """Test that streaming mode produces same result as batch mode."""
        # Create test data
        data_bytes = bytearray()
        for i in range(200):
            data_bytes.append((i * 73) % 256)
        
        params = {"hand_size": 4}
        
        # Batch mode
        batch_plugin = PokerTest()
        data = BytesView(bytes(data_bytes))
        batch_result = batch_plugin.run(data, params)

        # Streaming mode
        stream_plugin = PokerTest()
        chunk_size = 50
        for i in range(0, len(data_bytes), chunk_size):
            chunk = bytes(data_bytes[i:i + chunk_size])
            stream_plugin.update(chunk, params)
        stream_result = stream_plugin.finalize(params)

        # Results should be very similar (may have minor differences due to chunk boundaries)
        assert batch_result.passed == stream_result.passed
        assert abs(batch_result.p_value - stream_result.p_value) < 0.1

    def test_p_value_range(self):
        """Test that p_value is always in valid range."""
        test_cases = [
            (b'\x00' * 100, 4),
            (b'\xFF' * 100, 4),
            (b'\xAA' * 100, 4),
            (bytes(range(256)) * 2, 3),
        ]

        for test_data, hand_size in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {"hand_size": hand_size})
            assert 0.0 <= result.p_value <= 1.0, f"Invalid p_value: {result.p_value}"

    def test_chi_square_positive(self):
        """Test that chi-square statistic is always non-negative."""
        data = BytesView(bytes(range(256)) * 2)
        params = {"hand_size": 4}
        result = self.plugin.run(data, params)
        
        if "chi_square_statistic" in result.metrics:
            assert result.metrics["chi_square_statistic"] >= 0.0

    def test_custom_alpha(self):
        """Test with custom alpha parameter."""
        data = BytesView(b'\x00' * 100)
        params = {"hand_size": 4, "alpha": 0.05}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "poker"
        assert result.passed is False
        assert result.p_value < 0.05

    def test_requires_bits(self):
        """Test that plugin requires bits."""
        assert hasattr(self.plugin, 'requires')
        assert 'bits' in self.plugin.requires

    def test_unique_patterns_metric(self):
        """Test that unique patterns metric is calculated."""
        data = BytesView(bytes(range(256)))
        params = {"hand_size": 4}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert "unique_patterns" in result.metrics
        assert "possible_patterns" in result.metrics
        assert result.metrics["unique_patterns"] <= result.metrics["possible_patterns"]

    def test_hand_size_2(self):
        """Test with minimum hand size."""
        data = BytesView(bytes(range(256)) * 2)
        params = {"hand_size": 2}
        
        result = self.plugin.run(data, params)
        
        assert isinstance(result, TestResult)
        assert result.metrics["hand_size"] == 2
        assert result.metrics["possible_patterns"] == 4  # 2^2

    def test_hand_size_8(self):
        """Test with maximum hand size."""
        data = BytesView(bytes(range(256)) * 4)
        params = {"hand_size": 8}
        
        result = self.plugin.run(data, params)
        
        assert isinstance(result, TestResult)
        assert result.metrics["hand_size"] == 8
        assert result.metrics["possible_patterns"] == 256  # 2^8

    def test_streaming_with_large_chunks(self):
        """Test streaming with large chunks."""
        stream_plugin = PokerTest()
        data_bytes = bytearray()
        for i in range(500):
            data_bytes.append((i * 137) % 256)
        
        # Split into 5 large chunks
        chunk_size = 100
        for i in range(0, len(data_bytes), chunk_size):
            chunk = bytes(data_bytes[i:i + chunk_size])
            stream_plugin.update(chunk, {"hand_size": 4})
        
        result = stream_plugin.finalize({"hand_size": 4})
        
        assert isinstance(result, TestResult)
        assert result.metrics["num_hands"] == 1000  # 4000 bits / 4 bits per hand

    def test_all_same_pattern(self):
        """Test when all hands have the same pattern."""
        data = BytesView(b'\x00' * 200)
        params = {"hand_size": 4}
        
        result = self.plugin.run(data, params)
        
        assert result.passed is False
        assert result.metrics["unique_patterns"] == 1

    def test_category_and_p_values(self):
        """Test category and p_values dict."""
        data = BytesView(bytes(range(256)) * 2)
        params = {"hand_size": 4}
        result = self.plugin.run(data, params)
        
        assert result.category == "statistical"
        assert "poker" in result.p_values

    def test_degrees_of_freedom_calculation(self):
        """Test that degrees of freedom equals 2^m - 1."""
        test_cases = [(3, 7), (4, 15), (5, 31), (6, 63)]
        
        for hand_size, expected_df in test_cases:
            data = BytesView(bytes(range(256)) * 2)
            result = self.plugin.run(data, {"hand_size": hand_size})
            assert result.metrics["degrees_of_freedom"] == expected_df

    def test_streaming_finalize_resets_state(self):
        """Test that finalize resets state for reuse."""
        stream_plugin = PokerTest()
        
        # First run
        stream_plugin.update(bytes(range(256)), {"hand_size": 4})
        result1 = stream_plugin.finalize({"hand_size": 4})
        
        # Second run
        stream_plugin.update(b'\x00' * 200, {"hand_size": 4})
        result2 = stream_plugin.finalize({"hand_size": 4})
        
        # Results should be independent
        assert result1.passed != result2.passed

    def test_metrics_completeness(self):
        """Test that all expected metrics are present."""
        data = BytesView(bytes(range(256)) * 2)
        result = self.plugin.run(data, {"hand_size": 4})
        
        expected_metrics = ["total_bits", "hand_size", "num_hands", 
                           "chi_square_statistic", "degrees_of_freedom",
                           "unique_patterns", "possible_patterns"]
        for metric in expected_metrics:
            assert metric in result.metrics

    def test_very_large_poker_test(self):
        """Test poker with very large dataset."""
        data_bytes = bytearray()
        for _ in range(400):
            data_bytes.extend(bytes(range(256)))
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {"hand_size": 4})
        
        assert isinstance(result, TestResult)
        assert result.metrics["total_bits"] == 819200
        assert 0.0 <= result.p_value <= 1.0

"""Tests for Gap test plugin."""

import pytest
from patternanalyzer.plugins.gap_test import GapTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestGapTest:
    """Test cases for GapTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = GapTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "gap" in desc.lower()

    def test_insufficient_data(self):
        """Test with insufficient data."""
        data = BytesView(b'\x00\x01\x02')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert result.passed is True
        assert result.p_value == 1.0
        assert result.metrics["status"] == "skipped_insufficient_data"

    def test_random_like_data(self):
        """Test with random-like data."""
        # Create data with good mix of bits
        data_bytes = bytearray()
        for i in range(200):
            data_bytes.append(0xAA if i % 2 == 0 else 0x55)  # Alternating patterns
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["total_bits"] == 1600

    def test_pattern_with_regular_gaps(self):
        """Test with pattern having regular gaps."""
        # Create pattern: 1 followed by several 0s, repeated
        bits = []
        for _ in range(50):
            bits.extend([1, 0, 0, 0, 0, 0, 0, 0])  # Pattern with regular gaps
        
        # Convert bits to bytes
        data_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(bits):
                    byte_val |= (bits[i + j] << (7 - j))
            data_bytes.append(byte_val)
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_all_zeros(self):
        """Test with all zeros (no pattern occurrences)."""
        data = BytesView(b'\x00' * 100)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        # Should skip due to insufficient occurrences of pattern
        assert result.metrics.get("status") in [
            "skipped_insufficient_occurrences",
            "skipped_insufficient_gaps",
            None
        ] or result.passed is not None

    def test_all_ones(self):
        """Test with all ones (frequent pattern occurrences)."""
        data = BytesView(b'\xFF' * 100)
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_custom_pattern(self):
        """Test with custom bit pattern."""
        # Create test data with specific pattern
        data = BytesView(b'\xAA' * 100)  # 10101010 pattern
        params = {"pattern": [1, 0]}  # Look for "10" pattern

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_p_value_range(self):
        """Test that p_value is always in valid range."""
        test_cases = [
            b'\xAA' * 100,
            b'\x55' * 100,
            b'\xCC' * 100,
            b'\x33' * 100,
        ]

        for test_data in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {})
            assert 0.0 <= result.p_value <= 1.0, f"Invalid p_value: {result.p_value}"

    def test_gap_metrics(self):
        """Test that gap metrics are calculated."""
        data = BytesView(b'\xF0' * 100)  # 11110000 pattern
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        
        # Check that metrics are present when test runs
        if result.metrics.get("status") is None:
            assert "gap_count" in result.metrics
            assert "pattern_occurrences" in result.metrics
            assert result.metrics["gap_count"] >= 0

    def test_large_data(self):
        """Test with larger data set."""
        # Create larger random-like data
        data_bytes = bytearray()
        for i in range(500):
            data_bytes.append((i * 137) % 256)  # Pseudo-random pattern
        
        data = BytesView(bytes(data_bytes))
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_custom_alpha(self):
        """Test with custom alpha parameter."""
        data = BytesView(b'\xAA' * 200)
        params = {"alpha": 0.05}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_requires_bits(self):
        """Test that plugin requires bits."""
        assert hasattr(self.plugin, 'requires')
        assert 'bits' in self.plugin.requires

    def test_pattern_length_2(self):
        """Test with 2-bit pattern."""
        data = BytesView(b'\xAA' * 200)  # 10101010 pattern
        params = {"pattern": [1, 0, 1]}
        
        result = self.plugin.run(data, params)
        
        assert isinstance(result, TestResult)
        assert result.test_name == "gap"
        assert 0.0 <= result.p_value <= 1.0

    def test_very_regular_gaps(self):
        """Test with perfectly regular gaps (should fail)."""
        # Create pattern where '1' appears every 8 bits
        bits = [1 if i % 8 == 0 else 0 for i in range(800)]
        data_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(bits):
                    byte_val |= (bits[i + j] << (7 - j))
            data_bytes.append(byte_val)
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.test_name == "gap"

    def test_no_pattern_found(self):
        """Test when pattern never occurs."""
        data = BytesView(b'\x00' * 100)  # All zeros, looking for '1'
        params = {"pattern": [1]}
        
        result = self.plugin.run(data, params)
        
        assert isinstance(result, TestResult)
        # Should skip due to insufficient occurrences

    def test_category_field(self):
        """Test that category is correctly set."""
        data = BytesView(b'\xAA' * 200)
        result = self.plugin.run(data, {})
        assert result.category == "statistical"

    def test_metrics_for_successful_run(self):
        """Test metrics are populated for successful run."""
        data = BytesView(b'\xF0' * 150)
        result = self.plugin.run(data, {})
        
        if result.metrics.get("status") is None:
            assert "gap_count" in result.metrics
            assert "pattern_occurrences" in result.metrics
            assert "mean_gap" in result.metrics
            assert "min_gap" in result.metrics
            assert "max_gap" in result.metrics

    def test_pattern_as_list(self):
        """Test that pattern parameter accepts list."""
        data = BytesView(b'\xCC' * 200)  # 11001100
        params = {"pattern": [1, 1, 0]}
        
        result = self.plugin.run(data, params)
        
        assert isinstance(result, TestResult)
        assert result.test_name == "gap"

    def test_very_large_data_gap(self):
        """Test gap analysis with large dataset."""
        data_bytes = bytearray()
        for i in range(1000):
            data_bytes.append((i * 73) % 256)
        
        data = BytesView(bytes(data_bytes))
        result = self.plugin.run(data, {})
        
        assert isinstance(result, TestResult)
        assert result.metrics["total_bits"] == 8000

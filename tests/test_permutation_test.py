"""Tests for Permutation test plugin."""

import pytest
from patternanalyzer.plugins.permutation_test import PermutationTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestPermutationTest:
    """Test cases for PermutationTest."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = PermutationTest()

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "permutation" in desc.lower()

    def test_insufficient_blocks(self):
        """Test with insufficient data."""
        data = BytesView(b'\x00\x01\x02\x03\x04')
        params = {}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert result.passed is True
        assert result.p_value == 1.0
        assert result.metrics["status"] == "skipped_insufficient_blocks"

    def test_uniform_permutation_distribution(self):
        """Test with uniformly distributed permutations."""
        # Create data with good variety
        data_bytes = bytearray()
        for i in range(200):
            data_bytes.append((i * 137) % 256)
        
        data = BytesView(bytes(data_bytes))
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["block_size"] == 3

    def test_biased_permutation_distribution(self):
        """Test with biased permutation distribution."""
        # All zeros should have only one permutation
        data = BytesView(b'\x00' * 100)
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert result.passed is False  # Should fail for biased data
        assert 0.0 <= result.p_value <= 1.0
        assert result.p_value < 0.01

    def test_sequential_data(self):
        """Test with sequential byte values."""
        # Sequential data has consistent permutation pattern
        data = BytesView(bytes(range(100)))
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert 0.0 <= result.p_value <= 1.0

    def test_block_size_2(self):
        """Test with block size of 2."""
        data = BytesView(bytes(range(256)))
        params = {"block_size": 2}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["block_size"] == 2
        assert result.metrics["possible_permutations"] == 2  # 2!

    def test_block_size_4(self):
        """Test with block size of 4."""
        data = BytesView(bytes(range(256)))
        params = {"block_size": 4}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert 0.0 <= result.p_value <= 1.0
        assert result.metrics["block_size"] == 4
        assert result.metrics["possible_permutations"] == 24  # 4!

    def test_invalid_block_size_too_small(self):
        """Test with invalid block size (too small)."""
        data = BytesView(bytes(range(100)))
        params = {"block_size": 1}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert result.metrics["status"] == "skipped_invalid_block_size"

    def test_invalid_block_size_too_large(self):
        """Test with invalid block size (too large)."""
        data = BytesView(bytes(range(100)))
        params = {"block_size": 6}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert result.metrics["status"] == "skipped_invalid_block_size"

    def test_repeated_pattern(self):
        """Test with repeated byte pattern."""
        data = BytesView(b'\x10\x20\x30' * 50)
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        # Should fail as all blocks have same permutation
        assert result.passed is False
        assert 0.0 <= result.p_value <= 1.0

    def test_reverse_pattern(self):
        """Test with reverse ordered pattern."""
        data = BytesView(b'\x30\x20\x10' * 50)
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        # Should fail as all blocks have same permutation
        assert result.passed is False
        assert 0.0 <= result.p_value <= 1.0

    def test_p_value_range(self):
        """Test that p_value is always in valid range."""
        test_cases = [
            (b'\x00' * 100, 3),
            (bytes(range(100)), 3),
            (b'\x10\x20\x30' * 30, 3),
            (bytes([i % 50 for i in range(200)]), 4),
        ]

        for test_data, block_size in test_cases:
            data = BytesView(test_data)
            result = self.plugin.run(data, {"block_size": block_size})
            assert 0.0 <= result.p_value <= 1.0, f"Invalid p_value: {result.p_value}"

    def test_chi_square_positive(self):
        """Test that chi-square statistic is always non-negative."""
        data = BytesView(bytes(range(100)))
        params = {"block_size": 3}
        result = self.plugin.run(data, params)
        
        if "chi_square_statistic" in result.metrics:
            assert result.metrics["chi_square_statistic"] >= 0.0

    def test_custom_alpha(self):
        """Test with custom alpha parameter."""
        data = BytesView(b'\x00' * 100)
        params = {"block_size": 3, "alpha": 0.05}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert result.passed is False
        assert result.p_value < 0.05

    def test_unique_permutations_metric(self):
        """Test that unique permutations metric is calculated."""
        data = BytesView(bytes(range(100)))
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert "unique_permutations" in result.metrics
        assert "possible_permutations" in result.metrics
        assert result.metrics["unique_permutations"] <= result.metrics["possible_permutations"]

    def test_with_ties(self):
        """Test with byte blocks containing tied values."""
        # Blocks with repeated values
        data = BytesView(b'\x10\x10\x20' * 50)
        params = {"block_size": 3}

        result = self.plugin.run(data, params)

        assert isinstance(result, TestResult)
        assert result.test_name == "permutation"
        assert 0.0 <= result.p_value <= 1.0

    def test_permutation_to_id(self):
        """Test the permutation ID conversion."""
        # Test internal method
        perm_id_1 = self.plugin._permutation_to_id([0, 1, 2])
        perm_id_2 = self.plugin._permutation_to_id([2, 1, 0])
        
        # Different permutations should have different IDs
        assert perm_id_1 != perm_id_2
        
        # Same permutation should have same ID
        perm_id_3 = self.plugin._permutation_to_id([0, 1, 2])
        assert perm_id_1 == perm_id_3

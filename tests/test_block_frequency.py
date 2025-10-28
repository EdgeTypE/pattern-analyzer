"""Unit tests for BlockFrequencyTest plugin."""

import pytest
from patternanalyzer.plugins.block_frequency_test import BlockFrequencyTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestBlockFrequency:
    def setup_method(self):
        self.plugin = BlockFrequencyTest()

    def test_all_zeros(self):
        data = BytesView(b'\x00' * 16)  # 128 bits
        result = self.plugin.run(data, {"block_size": 8})
        assert isinstance(result, TestResult)
        assert result.test_name == "block_frequency"
        assert result.metrics["total_bits"] == 128
        assert result.metrics["block_count"] == 16
        assert result.metrics["block_size"] == 8
        assert result.metrics["ones_counts"][0] == 0
        assert 0.0 <= result.p_value <= 1.0
        assert result.passed is False

    def test_balanced_blocks(self):
        # each block 0xAA contains 4 ones out of 8 bits, so perfectly balanced per block
        data = BytesView(b'\xAA' * 16)
        result = self.plugin.run(data, {"block_size": 8})
        assert isinstance(result, TestResult)
        assert result.test_name == "block_frequency"
        assert result.metrics["block_count"] == 16
        assert all(p == 0.5 for p in result.metrics["proportions"])
        assert result.passed is True

    def test_small_block_size(self):
        data = BytesView(b'\xFF' * 2)  # 16 bits total
        # using block_size larger than data should short circuit
        result = self.plugin.run(data, {"block_size": 32})
        assert isinstance(result, TestResult)
        assert result.metrics["block_count"] == 0
        assert result.passed is True
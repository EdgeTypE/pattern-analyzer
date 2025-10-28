"""Unit tests for Random Excursions plugin (simplified)."""

import pytest
from patternanalyzer.plugins.random_excursions import RandomExcursionsTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestRandomExcursions:
    def setup_method(self):
        self.plugin = RandomExcursionsTest()

    def test_alternating_pattern_passes(self):
        """Alternating bits produce many excursions and should run the test."""
        data = BytesView(b'\xAA' * 16)  # 128 bits, 10101010...
        res = self.plugin.run(data, {})
        assert isinstance(res, TestResult)
        assert res.test_name == "random_excursions"
        assert "cycles" in res.metrics
        assert res.metrics["total_bits"] == 128
        assert res.metrics["total_visits"] > 0
        assert 0.0 <= res.p_value <= 1.0

    def test_all_zeros_skipped_for_no_cycles(self):
        """All zeros create no returns-to-zero and should be skipped due to insufficient cycles."""
        data = BytesView(b'\x00' * 16)
        res = self.plugin.run(data, {})
        assert isinstance(res, dict)
        assert res.get("status") == "skipped"
        assert "insufficient cycles" in res.get("reason", "") or "insufficient visits" in res.get("reason", "")

    def test_small_input_skipped(self):
        """Very small input should trigger the skipped path."""
        data = BytesView(b'\x00')  # 8 bits
        res = self.plugin.run(data, {})
        assert isinstance(res, dict)
        assert res.get("status") == "skipped"
        assert "insufficient" in res.get("reason", "").lower()
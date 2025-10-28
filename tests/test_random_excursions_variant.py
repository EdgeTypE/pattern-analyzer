"""Unit tests for Random Excursions Variant plugin (simplified)."""

import pytest
from patternanalyzer.plugins.random_excursions_variant import RandomExcursionsVariantTest
from patternanalyzer.plugin_api import BytesView, TestResult


class TestRandomExcursionsVariant:
    def setup_method(self):
        self.plugin = RandomExcursionsVariantTest()

    def test_balanced_pattern_passes(self):
        """Balanced pattern should produce visits across states and yield a p-value."""
        data = BytesView(b'\xAA' * 16)  # alternating bits
        res = self.plugin.run(data, {})
        assert isinstance(res, TestResult)
        assert res.test_name == "random_excursions_variant"
        assert res.metrics["total_bits"] == 128
        assert res.metrics["total_visits"] > 0
        assert 0.0 <= res.p_value <= 1.0

    def test_all_zeros_skipped(self):
        """All zeros should be skipped due to no visits."""
        data = BytesView(b'\x00' * 16)
        res = self.plugin.run(data, {})
        assert isinstance(res, dict)
        assert res.get("status") == "skipped"
        assert "insufficient" in res.get("reason", "").lower()

    def test_small_input_skipped(self):
        data = BytesView(b'\x00')
        res = self.plugin.run(data, {})
        assert isinstance(res, dict)
        assert res.get("status") == "skipped"
        assert "insufficient" in res.get("reason", "").lower()
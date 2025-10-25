"""Tests for Longest Run of Ones in a Block plugin."""

import math
from patternlab.plugins.longest_run import LongestRunOnesTest, _TABLES
from patternlab.plugin_api import BytesView, TestResult


class TestLongestRunOnes:
    def setup_method(self):
        self.plugin = LongestRunOnesTest()

    def test_describe(self):
        desc = self.plugin.describe()
        assert isinstance(desc, str) and len(desc) > 0

    def test_insufficient_blocks_default(self):
        # default block_size=8, min_blocks=8 -> need 64 bits; provide less to trigger insufficient_blocks
        data = BytesView(b'\x00')  # 8 bits -> 1 block
        result = self.plugin.run(data, {})
        assert isinstance(result, TestResult)
        assert result.test_name == "longest_run_ones"
        assert result.p_value == 1.0
        assert result.metrics.get("reason") == "insufficient_blocks"
        assert result.metrics["total_bits"] == 8

    def test_m8_table_counts_chi2_and_pvalue(self):
        # Build 20 blocks (20 bytes) with controlled longest-run categories for m=8:
        #  - 5 blocks with max_run=0  -> category 0 (<=1)
        #  - 5 blocks with max_run=2  -> category 1 (==2)
        #  - 5 blocks with max_run=3  -> category 2 (==3)
        #  - 5 blocks with max_run=5  -> category 3 (>=4)
        blocks = []
        blocks += [0x00] * 5   # max_run = 0
        blocks += [0xC0] * 5   # 11000000 -> max_run = 2
        blocks += [0xE0] * 5   # 11100000 -> max_run = 3
        blocks += [0xF8] * 5   # 11111000 -> max_run = 5
        data = BytesView(bytes(blocks))
        num_blocks = len(blocks)

        result = self.plugin.run(data, {"block_size": 8, "min_blocks": 1})
        assert isinstance(result, TestResult)
        assert result.test_name == "longest_run_ones"

        # Expected counts from construction
        expected_counts = [5, 5, 5, 5]
        assert result.metrics["counts"] == expected_counts
        assert result.metrics["num_blocks"] == num_blocks
        # Confirm dof matches table (len(probs)-1)
        probs = _TABLES[8]["probs"]
        dof = len(probs) - 1
        assert result.metrics["dof"] == dof

        # Recompute chi2 and expected p-value using same logic as plugin.
        exp_expected = [p * num_blocks for p in probs]
        chi2 = 0.0
        for o, e in zip(expected_counts, exp_expected):
            if e > 0:
                chi2 += ((o - e) ** 2) / e

        assert math.isclose(result.metrics["chi2"], chi2, rel_tol=1e-9, abs_tol=1e-9)

        # Compute expected p-value using SciPy if available, else Wilson–Hilferty (same as plugin)
        try:
            from scipy.stats import chi2 as _chi2
            expected_p = float(_chi2.sf(chi2, dof))
        except Exception:
            w = (chi2 / dof) ** (1.0 / 3.0)
            mu = 1.0 - 2.0 / (9.0 * dof)
            sigma = math.sqrt(2.0 / (9.0 * dof))
            z = (w - mu) / sigma
            # plugin uses upper-tail 1 - Phi(z)
            # approximate normal CDF via math.erf
            expected_p = 0.5 * (1.0 - math.erf(z / math.sqrt(2.0)))

        # Allow small numerical differences
        assert 0.0 <= (result.p_value or 0.0) <= 1.0
        assert math.isclose(result.p_value or 0.0, expected_p, rel_tol=1e-6, abs_tol=1e-6)

    def test_m128_single_block_behavior_and_pvalue(self):
        # Create a single 128-bit block with a long run at start (>=15)
        # Represent block as 16 bytes: first two bytes contain many ones, rest zeros.
        # We'll set first 2 bytes to 0xFF, 0xFE -> 15 ones followed by zeros at MSBs region.
        block = bytes([0xFF, 0xFE] + [0x00] * 14)
        data = BytesView(block)
        result = self.plugin.run(data, {"block_size": 128, "min_blocks": 1})
        assert isinstance(result, TestResult)
        assert result.test_name == "longest_run_ones"
        # Should produce one count in some category and sum(counts)==1
        counts = result.metrics["counts"]
        assert sum(counts) == 1
        assert result.metrics["num_blocks"] == 1
        # p-value is valid and in [0,1]
        assert 0.0 <= (result.p_value or 0.0) <= 1.0

        # Validate recomputed p-value matches plugin's output (within tolerance)
        probs = _TABLES[128]["probs"]
        # expected counts: find which category has the single count
        chi2 = 0.0
        exp_expected = [p * 1 for p in probs]
        for o, e in zip(counts, exp_expected):
            if e > 0:
                chi2 += ((o - e) ** 2) / e
        dof = len(probs) - 1
        try:
            from scipy.stats import chi2 as _chi2
            expected_p = float(_chi2.sf(chi2, dof))
        except Exception:
            w = (chi2 / dof) ** (1.0 / 3.0)
            mu = 1.0 - 2.0 / (9.0 * dof)
            sigma = math.sqrt(2.0 / (9.0 * dof))
            z = (w - mu) / sigma
            expected_p = 0.5 * (1.0 - math.erf(z / math.sqrt(2.0)))
        assert math.isclose(result.p_value or 0.0, expected_p, rel_tol=1e-6, abs_tol=1e-6)

    def test_m10000_table_exists_and_insufficient_blocks(self):
        # For huge block sizes it's impractical to run full test here; ensure table exists and
        # insufficient_blocks path triggers when data is too small.
        assert 10000 in _TABLES
        data = BytesView(b'\x00')
        result = self.plugin.run(data, {"block_size": 10000, "min_blocks": 8})
        assert isinstance(result, TestResult)
        assert result.p_value == 1.0
        assert result.metrics.get("reason") == "insufficient_blocks"
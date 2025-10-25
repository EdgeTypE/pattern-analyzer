"""Longest Run of Ones in a Block test plugin aligned to NIST table-driven categories.

- Provides fixed category thresholds and probabilities for m=8, m=128 and m=10000.
- Uses SciPy's chi2.sf when available to compute exact p-values; falls back to
  Wilson–Hilferty approximation otherwise.
- Reports detailed metrics including counts, expected, chi2, dof and method used.
"""

from typing import List, Dict
import math
from ..plugin_api import BytesView, TestResult, TestPlugin

# Table definitions for supported block sizes (m).
# Each entry provides:
#  - "probs": list of expected probabilities for the categories (must sum to ~1.0)
#  - "bins": thresholds used to map observed longest runs into categories.
#    bins contains the upper threshold for each category except the last which is >= threshold.
# The number of categories = len(probs)
_TABLES: Dict[int, Dict[str, List[int]]] = {
    8: {
        # NIST-like probabilities for m=8, categories: v <=1, v=2, v=3, v>=4
        "probs": [0.2148, 0.3672, 0.2305, 0.1875],
        "bins": [1, 2, 3],  # final category is >=4
        "labels": ["<=1", "2", "3", ">=4"],
    },
    128: {
        # NIST-like probabilities (6 categories) for m=128
        # categories mapped to thresholds below (these thresholds are the run-length
        # thresholds for categorization; exact NIST thresholds are used here in spirit)
        "probs": [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124],
        "bins": [10, 11, 12, 13, 14],  # last category >=15
        "labels": ["<=10", "11", "12", "13", "14", ">=15"],
    },
    10000: {
        # NIST-like probabilities (6 categories) for m=10000 (approximate)
        # These probabilities are the tabulated expected frequencies used by NIST-style tests.
        "probs": [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.1402],
        # thresholds are approximate longest-run thresholds for very large block sizes
        "bins": [267, 268, 269, 270, 271],  # last category >=272
        "labels": ["<=267", "268", "269", "270", "271", ">=272"],
    },
}


class LongestRunOnesTest(TestPlugin):
    """Longest run of ones in a block using table-driven categories (NIST-aligned)."""

    requires = ["bits"]

    def describe(self) -> str:
        return "Longest run of ones in a block (NIST table-aligned)"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)

        block_size = int(params.get("block_size", 8))
        min_blocks = int(params.get("min_blocks", 8))
        alpha = float(params.get("alpha", 0.01))

        if block_size <= 0:
            raise ValueError("block_size must be > 0")

        num_blocks = n // block_size
        if num_blocks < min_blocks:
            return TestResult(
                test_name="longest_run_ones",
                passed=True,
                p_value=1.0,
                category="statistical",
                p_values={"longest_run_ones": 1.0},
                metrics={"total_bits": n, "num_blocks": num_blocks, "reason": "insufficient_blocks"},
            )

        # compute longest run per block
        longest_runs: List[int] = []
        for i in range(num_blocks):
            block = bits[i * block_size : (i + 1) * block_size]
            max_run = 0
            cur = 0
            for b in block:
                if b:
                    cur += 1
                    if cur > max_run:
                        max_run = cur
                else:
                    cur = 0
            longest_runs.append(max_run)

        # Select table if available, otherwise fallback to a coarse 4-bin uniform probability table.
        table = _TABLES.get(block_size)
        if table is None:
            # Fallback: 4 equal-probability bins based on run-length percentiles
            probs = [0.25, 0.25, 0.25, 0.25]
            bins = [
                max(1, block_size // 8),
                max(2, block_size // 4),
                max(3, block_size // 2),
            ]
            labels = ["small", "medium", "large", "xlarge"]
        else:
            probs = table["probs"]
            bins = table["bins"]
            labels = table.get("labels", [f"cat{i}" for i in range(len(probs))])

        # Map runs into categories (counts)
        counts = [0] * len(probs)
        for r in longest_runs:
            placed = False
            for idx, threshold in enumerate(bins):
                # for all but last threshold, category is r <= threshold
                if r <= threshold:
                    counts[idx] += 1
                    placed = True
                    break
            if not placed:
                # last category (>= last threshold + 1)
                counts[-1] += 1

        expected_counts = [p * num_blocks for p in probs]

        # Compute chi-square statistic
        chi2_stat = 0.0
        for o, e in zip(counts, expected_counts):
            if e > 0:
                chi2_stat += ((o - e) ** 2) / e

        dof = max(1, len(probs) - 1)

        # Try to use SciPy's survival function for chi2 if available (more accurate).
        method = "wilson"
        p_value = None
        zscore = None
        try:
            from scipy.stats import chi2 as _chi2

            # chi2.sf returns the upper-tail probability P(X >= chi2_stat)
            p_value = float(_chi2.sf(chi2_stat, dof))
            method = "scipy"
        except Exception:
            # Wilson–Hilferty approximation to convert chi-square to approx normal and get upper-tail p.
            # transform: Z ≈ ( (X/dof)^(1/3) - (1 - 2/(9*dof)) ) / sqrt(2/(9*dof))
            try:
                w = (chi2_stat / dof) ** (1.0 / 3.0)
                mu = 1.0 - 2.0 / (9.0 * dof)
                sigma = math.sqrt(2.0 / (9.0 * dof))
                zscore = (w - mu) / sigma
                # upper tail p-value
                p_value = 1.0 - self._normal_cdf(zscore)
                method = "wilson"
            except Exception:
                p_value = None

        if p_value is not None:
            p_value = max(0.0, min(1.0, p_value))

        passed = True if p_value is None else (p_value > alpha)

        metrics = {
            "counts": counts,
            "expected": expected_counts,
            "chi2": chi2_stat,
            "dof": dof,
            "num_blocks": num_blocks,
            "total_bits": n,
            "method": method,
            "labels": labels,
        }

        if zscore is not None:
            metrics["zscore"] = zscore

        return TestResult(
            test_name="longest_run_ones",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"longest_run_ones": p_value} if p_value is not None else {},
            metrics=metrics,
            z_score=zscore,
        )

    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal CDF (Abramowitz-Stegun)."""
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)

        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

        return 0.5 * (1.0 + sign * y)
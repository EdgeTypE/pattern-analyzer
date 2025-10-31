"""Gap test plugin for randomness.

The Gap test examines the distances (gaps) between occurrences of specific
patterns in the bit sequence. For random data, the gap lengths should follow
a geometric distribution. Uses chi-square to test the fit.
"""

import math
from collections import Counter
from typing import Dict, Any, List

try:
    from ..plugin_api import BytesView, TestResult, TestPlugin
except Exception:
    from patternanalyzer.plugin_api import BytesView, TestResult, TestPlugin  # type: ignore


class GapTest(TestPlugin):
    """Gap test for randomness of bit sequences."""

    requires = ['bits']

    def __init__(self):
        """Initialize the plugin."""
        pass

    def describe(self) -> str:
        """Return plugin description."""
        return "Gap test analyzing distances between occurrences of bit patterns"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run Gap test in batch mode."""
        bits = data.bit_view()
        n = len(bits)

        if n < 100:
            # Need sufficient data for gap analysis
            return TestResult(
                test_name="gap",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "status": "skipped_insufficient_data",
                },
            )

        # Pattern to search for (default: '1' bit)
        pattern_bits = params.get("pattern", [1])
        if isinstance(pattern_bits, int):
            pattern_bits = [pattern_bits]
        
        pattern_len = len(pattern_bits)
        
        if pattern_len > n // 10:
            # Pattern too long for meaningful analysis
            return TestResult(
                test_name="gap",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "pattern_length": pattern_len,
                    "status": "skipped_pattern_too_long",
                },
            )

        # Find all occurrences of the pattern
        occurrences = []
        for i in range(n - pattern_len + 1):
            if bits[i:i+pattern_len] == pattern_bits:
                occurrences.append(i)

        if len(occurrences) < 10:
            # Need sufficient occurrences for gap analysis
            return TestResult(
                test_name="gap",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "pattern_occurrences": len(occurrences),
                    "status": "skipped_insufficient_occurrences",
                },
            )

        # Calculate gaps between consecutive occurrences
        gaps = []
        for i in range(len(occurrences) - 1):
            gap = occurrences[i + 1] - occurrences[i] - pattern_len
            if gap >= 0:
                gaps.append(gap)

        if len(gaps) < 5:
            return TestResult(
                test_name="gap",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "gap_count": len(gaps),
                    "status": "skipped_insufficient_gaps",
                },
            )

        # Define gap categories (bins)
        # For geometric distribution with parameter p
        # P(gap = k) = (1-p)^k * p
        p = len(occurrences) / (n - pattern_len + 1)  # Estimate of pattern probability
        
        # Create bins: [0], [1], [2], ..., [max_gap-1], [max_gap, ∞)
        max_individual_gap = 10
        bins = list(range(max_individual_gap + 1)) + [float('inf')]
        
        # Count observed gaps in each bin
        observed_counts = [0] * (len(bins) - 1)
        for gap in gaps:
            for i in range(len(bins) - 1):
                if gap < bins[i + 1]:
                    observed_counts[i] += 1
                    break

        # Calculate expected counts using geometric distribution
        total_gaps = len(gaps)
        expected_counts = []
        
        for i in range(len(bins) - 1):
            if bins[i + 1] == float('inf'):
                # Last bin: P(gap >= max_individual_gap)
                prob = (1 - p) ** max_individual_gap
            else:
                # P(gap = k) = (1-p)^k * p
                prob = ((1 - p) ** bins[i]) * p
            expected_counts.append(prob * total_gaps)

        # Merge bins with low expected counts
        merged_observed = []
        merged_expected = []
        current_obs = 0
        current_exp = 0.0
        
        for obs, exp in zip(observed_counts, expected_counts):
            current_obs += obs
            current_exp += exp
            if current_exp >= 5.0 or exp == expected_counts[-1]:
                merged_observed.append(current_obs)
                merged_expected.append(current_exp)
                current_obs = 0
                current_exp = 0.0
        
        if current_obs > 0 or current_exp > 0:
            if merged_expected:
                merged_observed[-1] += current_obs
                merged_expected[-1] += current_exp
            else:
                merged_observed.append(current_obs)
                merged_expected.append(current_exp)

        # Calculate chi-square statistic
        chi_square = 0.0
        for obs, exp in zip(merged_observed, merged_expected):
            if exp > 0:
                chi_square += ((obs - exp) ** 2) / exp

        # Degrees of freedom = number of bins - 1 (minus 1 for estimated parameter)
        df = max(1, len(merged_observed) - 2)
        
        # Calculate p-value
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="gap",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bits": n,
                "pattern_length": pattern_len,
                "pattern_occurrences": len(occurrences),
                "gap_count": len(gaps),
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "mean_gap": sum(gaps) / len(gaps) if gaps else 0.0,
                "min_gap": min(gaps) if gaps else 0,
                "max_gap": max(gaps) if gaps else 0,
            },
            p_values={"gap": p_value},
        )

    def _chi_square_cdf(self, x: float, df: int) -> float:
        """Approximate chi-square cumulative distribution function."""
        if x <= 0:
            return 0.0
        
        if df > 100:
            # Wilson-Hilferty transformation for large df
            z = ((x / df) ** (1.0/3.0) - (1.0 - 2.0/(9.0*df))) / math.sqrt(2.0/(9.0*df))
            return self._normal_cdf(z)
        
        # Use incomplete gamma function
        return self._gamma_cdf(x / 2.0, df / 2.0)

    def _gamma_cdf(self, x: float, k: float) -> float:
        """Approximate gamma CDF."""
        if x <= 0:
            return 0.0
        
        if x * k < 1.0:
            return self._gamma_series(x, k)
        else:
            return 1.0 - self._gamma_cf(x, k)

    def _gamma_series(self, x: float, k: float) -> float:
        """Series expansion for lower incomplete gamma."""
        max_iter = 1000
        epsilon = 1e-10
        
        result = 1.0 / k
        term = result
        
        for n in range(1, max_iter):
            term *= x / (k + n)
            result += term
            if abs(term) < epsilon:
                break
        
        return result * math.exp(-x + k * math.log(x) - math.lgamma(k))

    def _gamma_cf(self, x: float, k: float) -> float:
        """Continued fraction for upper incomplete gamma."""
        max_iter = 1000
        epsilon = 1e-10
        tiny = 1e-30
        
        b = x + 1.0 - k
        c = 1.0 / tiny
        d = 1.0 / b
        h = d
        
        for i in range(1, max_iter):
            a = -i * (i - k)
            b += 2.0
            d = a * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + a / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < epsilon:
                break
        
        return h * math.exp(-x + k * math.log(x) - math.lgamma(k))

    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal CDF."""
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

"""Poker test plugin for randomness.

The Poker test divides the bit sequence into fixed-size segments (hands)
and examines the distribution of different patterns within each hand.
It uses chi-square to compare observed pattern frequencies with expected values.
"""

import math
from collections import Counter
from typing import Dict, Any

try:
    from ..plugin_api import BytesView, TestResult, TestPlugin
except Exception:
    from patternanalyzer.plugin_api import BytesView, TestResult, TestPlugin  # type: ignore


class PokerTest(TestPlugin):
    """Poker test for randomness of bit sequences."""

    requires = ['bits']

    def __init__(self):
        """Initialize the plugin with streaming state."""
        # Streaming accumulators
        self._pattern_counts = Counter()
        self._total_hands = 0
        self._hand_size = 4  # Default hand size

    def describe(self) -> str:
        """Return plugin description."""
        return "Poker test analyzing pattern distribution in fixed-size bit segments"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run Poker test in batch mode."""
        bits = data.bit_view()
        n = len(bits)

        # Hand size (m bits per hand)
        hand_size = params.get("hand_size", 4)
        
        if hand_size < 2 or hand_size > 8:
            # Practical limits for hand size
            return TestResult(
                test_name="poker",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "hand_size": hand_size,
                    "status": "skipped_invalid_hand_size",
                },
            )

        # Number of complete hands
        num_hands = n // hand_size
        
        if num_hands < 50:
            # Need sufficient hands for meaningful analysis
            return TestResult(
                test_name="poker",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bits": n,
                    "hand_size": hand_size,
                    "num_hands": num_hands,
                    "status": "skipped_insufficient_hands",
                },
            )

        # Count pattern frequencies
        pattern_counts = Counter()
        for i in range(num_hands):
            start = i * hand_size
            hand = tuple(bits[start:start + hand_size])
            pattern_counts[hand] += 1

        # Calculate observed frequencies
        num_patterns = 2 ** hand_size
        expected_count = num_hands / num_patterns
        
        # Calculate chi-square statistic
        chi_square = 0.0
        for pattern in range(num_patterns):
            # Convert pattern number to tuple of bits
            pattern_tuple = tuple((pattern >> i) & 1 for i in range(hand_size - 1, -1, -1))
            observed = pattern_counts.get(pattern_tuple, 0)
            chi_square += ((observed - expected_count) ** 2) / expected_count

        # Degrees of freedom = 2^m - 1
        df = num_patterns - 1
        
        # Calculate p-value
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Ensure p_value is in valid range [0, 1]
        p_value = max(0.0, min(1.0, p_value))
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        # Calculate additional metrics
        unique_patterns = len(pattern_counts)
        
        return TestResult(
            test_name="poker",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bits": n,
                "hand_size": hand_size,
                "num_hands": num_hands,
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "unique_patterns": unique_patterns,
                "possible_patterns": num_patterns,
            },
            p_values={"poker": p_value},
        )

    def update(self, chunk: bytes, params: dict) -> None:
        """Update internal accumulators with a chunk of raw bytes."""
        if not chunk:
            return
        
        from ..plugin_api import BytesView
        bv = BytesView(chunk)
        bits = bv.bit_view()
        
        # Get hand size from params (or use instance default)
        hand_size = params.get("hand_size", self._hand_size)
        
        # Process complete hands only
        num_hands = len(bits) // hand_size
        
        for i in range(num_hands):
            start = i * hand_size
            hand = tuple(bits[start:start + hand_size])
            self._pattern_counts[hand] += 1
        
        self._total_hands += num_hands
        self._hand_size = hand_size

    def finalize(self, params: dict) -> TestResult:
        """Finalize streaming aggregation and return TestResult."""
        num_hands = self._total_hands
        hand_size = params.get("hand_size", self._hand_size)
        pattern_counts = self._pattern_counts
        
        # Reset accumulators for possible reuse
        self._pattern_counts = Counter()
        self._total_hands = 0

        if num_hands < 50:
            return TestResult(
                test_name="poker",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "hand_size": hand_size,
                    "num_hands": num_hands,
                    "status": "skipped_insufficient_hands",
                },
            )

        # Calculate observed frequencies
        num_patterns = 2 ** hand_size
        expected_count = num_hands / num_patterns
        
        # Calculate chi-square statistic
        chi_square = 0.0
        for pattern in range(num_patterns):
            # Convert pattern number to tuple of bits
            pattern_tuple = tuple((pattern >> i) & 1 for i in range(hand_size - 1, -1, -1))
            observed = pattern_counts.get(pattern_tuple, 0)
            chi_square += ((observed - expected_count) ** 2) / expected_count

        # Degrees of freedom = 2^m - 1
        df = num_patterns - 1
        
        # Calculate p-value
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Ensure p_value is in valid range [0, 1]
        p_value = max(0.0, min(1.0, p_value))
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        unique_patterns = len(pattern_counts)
        
        return TestResult(
            test_name="poker",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "hand_size": hand_size,
                "num_hands": num_hands,
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "unique_patterns": unique_patterns,
                "possible_patterns": num_patterns,
            },
            p_values={"poker": p_value},
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

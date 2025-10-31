"""Chi-Square test plugin for uniformity of byte distribution.

The Chi-Square test checks whether the observed byte frequency distribution
significantly deviates from the expected uniform distribution. A low p-value
indicates the data is non-random or biased.
"""

import math
from collections import Counter
from typing import Dict, Any

try:
    from ..plugin_api import BytesView, TestResult, TestPlugin
except Exception:
    from patternanalyzer.plugin_api import BytesView, TestResult, TestPlugin  # type: ignore


class ChiSquareTest(TestPlugin):
    """Chi-Square test for byte frequency uniformity."""

    def __init__(self):
        """Initialize the plugin with streaming state."""
        # Streaming accumulators
        self._counter = Counter()
        self._total_bytes = 0

    def describe(self) -> str:
        """Return plugin description."""
        return "Chi-Square test for uniformity of byte distribution"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run Chi-Square test in batch mode."""
        data_bytes = data.to_bytes()
        n = len(data_bytes)

        if n == 0:
            return TestResult(
                test_name="chi_square",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={"total_bytes": 0, "chi_square_statistic": 0.0},
            )

        # Count frequency of each byte value
        counter = Counter(data_bytes)
        
        # Expected frequency for uniform distribution
        expected = n / 256.0
        
        # Calculate chi-square statistic
        chi_square = sum((count - expected) ** 2 / expected for count in counter.values())
        
        # Add missing byte values (count = 0) to chi-square
        observed_bytes = len(counter)
        missing_bytes = 256 - observed_bytes
        if missing_bytes > 0:
            chi_square += missing_bytes * expected
        
        # Degrees of freedom = 256 - 1 = 255
        df = 255
        
        # Calculate p-value using chi-square CDF
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="chi_square",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bytes": n,
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "unique_bytes": observed_bytes,
            },
            p_values={"chi_square": p_value},
        )

    def update(self, chunk: bytes, params: dict) -> None:
        """Update internal accumulators with a chunk of raw bytes."""
        if not chunk:
            return
        self._counter.update(chunk)
        self._total_bytes += len(chunk)

    def finalize(self, params: dict) -> TestResult:
        """Finalize streaming aggregation and return TestResult."""
        n = self._total_bytes
        counter = self._counter
        
        # Reset accumulators for possible reuse
        self._counter = Counter()
        self._total_bytes = 0

        if n == 0:
            return TestResult(
                test_name="chi_square",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={"total_bytes": 0, "chi_square_statistic": 0.0},
            )

        # Expected frequency for uniform distribution
        expected = n / 256.0
        
        # Calculate chi-square statistic
        chi_square = sum((count - expected) ** 2 / expected for count in counter.values())
        
        # Add missing byte values (count = 0) to chi-square
        observed_bytes = len(counter)
        missing_bytes = 256 - observed_bytes
        if missing_bytes > 0:
            chi_square += missing_bytes * expected
        
        # Degrees of freedom = 256 - 1 = 255
        df = 255
        
        # Calculate p-value using chi-square CDF
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="chi_square",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bytes": n,
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "unique_bytes": observed_bytes,
            },
            p_values={"chi_square": p_value},
        )

    def _chi_square_cdf(self, x: float, df: int) -> float:
        """Approximate chi-square cumulative distribution function.
        
        Uses the relationship between chi-square and gamma distribution.
        For large df, uses normal approximation.
        """
        if x <= 0:
            return 0.0
        
        if df > 100:
            # Wilson-Hilferty transformation for large df
            z = ((x / df) ** (1.0/3.0) - (1.0 - 2.0/(9.0*df))) / math.sqrt(2.0/(9.0*df))
            return self._normal_cdf(z)
        
        # Use incomplete gamma function for small to medium df
        return self._gamma_cdf(x / 2.0, df / 2.0)

    def _gamma_cdf(self, x: float, k: float) -> float:
        """Approximate gamma CDF using incomplete gamma function."""
        if x <= 0:
            return 0.0
        
        # Use series expansion for small x*k, continued fraction for large x*k
        if x * k < 1.0:
            # Series expansion
            return self._gamma_series(x, k)
        else:
            # Continued fraction
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
        
        # Lentz's algorithm
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
        """Approximation of standard normal cumulative distribution function."""
        # Abramowitz and Stegun approximation
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

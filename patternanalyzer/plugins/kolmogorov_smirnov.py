"""Kolmogorov-Smirnov test plugin for uniformity.

The Kolmogorov-Smirnov (K-S) test checks whether the cumulative distribution
of byte values matches the expected uniform distribution. It's a non-parametric
test that measures the maximum deviation between observed and expected CDFs.
"""

import math
from typing import Dict, Any

try:
    from ..plugin_api import BytesView, TestResult, TestPlugin
except Exception:
    from patternanalyzer.plugin_api import BytesView, TestResult, TestPlugin  # type: ignore


class KolmogorovSmirnovTest(TestPlugin):
    """Kolmogorov-Smirnov test for byte value uniformity."""

    def describe(self) -> str:
        """Return plugin description."""
        return "Kolmogorov-Smirnov test for uniformity of byte distribution"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run K-S test in batch mode."""
        data_bytes = data.to_bytes()
        n = len(data_bytes)

        if n == 0:
            return TestResult(
                test_name="kolmogorov_smirnov",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={"total_bytes": 0, "ks_statistic": 0.0},
            )

        # Sort the byte values
        sorted_bytes = sorted(data_bytes)
        
        # Calculate empirical CDF at each unique value
        # Expected CDF for uniform distribution: F(x) = (x + 1) / 256
        max_deviation = 0.0
        
        for i, byte_val in enumerate(sorted_bytes):
            # Empirical CDF at this point
            empirical_cdf = (i + 1) / n
            
            # Expected CDF for uniform distribution over [0, 255]
            expected_cdf = (byte_val + 1) / 256.0
            
            # Calculate deviation
            deviation = abs(empirical_cdf - expected_cdf)
            max_deviation = max(max_deviation, deviation)
        
        # K-S statistic
        ks_statistic = max_deviation
        
        # Calculate p-value using K-S distribution
        # For large n, use asymptotic approximation
        p_value = self._ks_pvalue(ks_statistic, n)
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="kolmogorov_smirnov",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bytes": n,
                "ks_statistic": ks_statistic,
                "max_deviation": max_deviation,
            },
            p_values={"kolmogorov_smirnov": p_value},
        )

    def _ks_pvalue(self, d: float, n: int) -> float:
        """Calculate p-value for K-S statistic using asymptotic formula.
        
        Uses the Kolmogorov distribution for large n.
        """
        if d <= 0:
            return 1.0
        
        if n < 1:
            return 1.0
        
        # For small samples, use exact distribution (simplified)
        if n < 35:
            # Use a conservative approximation
            lambda_val = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * d
        else:
            # Asymptotic approximation: λ = sqrt(n) * D
            lambda_val = math.sqrt(n) * d
        
        # Calculate p-value using Kolmogorov distribution
        # P(D > d) ≈ 2 * sum_{k=1}^∞ (-1)^(k-1) * exp(-2k²λ²)
        # We compute a few terms for practical convergence
        p_value = 0.0
        max_terms = 100
        
        for k in range(1, max_terms + 1):
            term = (-1) ** (k - 1) * math.exp(-2 * k * k * lambda_val * lambda_val)
            p_value += term
            # Stop if terms become negligible
            if abs(term) < 1e-10:
                break
        
        p_value *= 2.0
        
        # Ensure p-value is in valid range
        p_value = max(0.0, min(1.0, p_value))
        
        return p_value

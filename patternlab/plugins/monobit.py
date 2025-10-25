"""Monobit test plugin."""

import math
from ..plugin_api import BytesView, TestResult, TestPlugin


class MonobitTest(TestPlugin):
    """Monobit frequency test plugin."""

    requires = ['bits']

    def __init__(self):
        # Streaming accumulators
        self._total_bits = 0
        self._ones_total = 0

    def describe(self) -> str:
        """Return plugin description."""
        return "Monobit frequency test for binary sequences"

    # Batch API (unchanged)
    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run monobit test (batch mode)."""
        bits = data.bit_view()
        n = len(bits)
        ones_count = sum(bits)

        if n == 0:
            return TestResult(
                test_name="monobit",
                passed=True,
                p_value=1.0,
                category="statistical",
                z_score=0.0,
                metrics={"ones_count": 0, "total_bits": 0},
            )
        z = (2 * ones_count - n) / math.sqrt(n)
        p = 2 * (1 - self._normal_cdf(abs(z)))
        passed = p > float(params.get("alpha", 0.01))
        return TestResult(
            test_name="monobit",
            passed=passed,
            p_value=p,
            category="statistical",
            z_score=z,
            metrics={"ones_count": ones_count, "total_bits": n},
            p_values={"monobit": p},
        )

    # Streaming API
    def update(self, chunk: bytes, params: dict) -> None:
        """Update internal accumulators with a chunk of raw bytes."""
        if not chunk:
            return
        bv = BytesView(chunk)
        bits = bv.bit_view()
        self._total_bits += len(bits)
        self._ones_total += sum(bits)

    def finalize(self, params: dict) -> TestResult:
        """Finalize streaming aggregation and return TestResult."""
        n = self._total_bits
        ones_count = self._ones_total
        # Reset accumulators for possible reuse
        self._total_bits = 0
        self._ones_total = 0

        if n == 0:
            return TestResult(
                test_name="monobit",
                passed=True,
                p_value=1.0,
                category="statistical",
                z_score=0.0,
                metrics={"ones_count": 0, "total_bits": 0},
            )
        z = (2 * ones_count - n) / math.sqrt(n)
        p = 2 * (1 - self._normal_cdf(abs(z)))
        passed = p > float(params.get("alpha", 0.01))
        return TestResult(
            test_name="monobit",
            passed=passed,
            p_value=p,
            category="statistical",
            z_score=z,
            metrics={"ones_count": ones_count, "total_bits": n},
            p_values={"monobit": p},
        )

    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal cumulative distribution function."""
        # Abramowitz and Stegun approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        # Save sign and take absolute value
        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)

        # A&S formula 7.1.26
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

        return 0.5 * (1.0 + sign * y)
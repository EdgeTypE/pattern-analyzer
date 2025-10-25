"""Runs test plugin (Wald–Wolfowitz)."""

import math
from typing import List
from ..plugin_api import BytesView, TestResult, TestPlugin


class RunsTest(TestPlugin):
    """Wald–Wolfowitz runs test implementation."""

    requires = ['bits']

    def describe(self) -> str:
        return "Runs test (Wald–Wolfowitz) for binary sequences"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Execute runs test."""
        bits = data.bit_view()

        total_bits = len(bits)
        ones = sum(1 for b in bits if b)
        zeros = total_bits - ones

        min_bits = int(params.get('min_bits', 20))
        if total_bits < min_bits:
            return TestResult(
                test_name="runs",
                passed=True,
                p_value=1.0,
                p_values={"runs": 1.0},
                metrics={"ones": ones, "zeros": zeros, "runs": 0, "total_bits": total_bits},
            )

        # count runs
        runs = 0
        prev = None
        for b in bits:
            if prev is None or b != prev:
                runs += 1
            prev = b

        n = total_bits
        n1 = ones
        n2 = zeros

        # expected runs and variance (approximation)
        expected_runs = (2.0 * n1 * n2) / n + 1.0
        denom = (n * n * (n - 1)) if n > 1 else 1.0
        variance = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n)) / denom if n > 1 else 0.0

        if variance <= 0.0:
            p_value = 1.0
            z_score = 0.0
        else:
            z_score = (runs - expected_runs) / math.sqrt(variance)
            abs_z = abs(z_score)
            p_value = 2.0 * (1.0 - self._normal_cdf(abs_z))

        passed = p_value > float(params.get('alpha', 0.01))

        return TestResult(
            test_name="runs",
            passed=passed,
            p_value=p_value,
            p_values={"runs": p_value},
            metrics={"ones": ones, "zeros": zeros, "runs": runs, "total_bits": total_bits},
            z_score=z_score
        )

    def _normal_cdf(self, x: float) -> float:
        """Approximation of the standard normal CDF (Abramowitz-Stegun)."""
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
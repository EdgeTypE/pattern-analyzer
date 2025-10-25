"""Cumulative Sums (Cusum) test plugin."""

import math
from ..plugin_api import BytesView, TestResult, TestPlugin


class CumulativeSumsTest(TestPlugin):
    """Cumulative sums test (NIST approximate)."""

    requires = ['bits']

    def describe(self) -> str:
        return "Cumulative sums (Cusum) test for binary sequences"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)

        # Minimum data size (NIST recommends reasonably large n; default 100)
        min_bits = int(params.get('min_bits', 100))
        if n < min_bits:
            return TestResult(
                test_name="cusum",
                passed=True,
                p_value=1.0,
                p_values={"cusum_forward": 1.0, "cusum_backward": 1.0, "cusum": 1.0},
                metrics={"total_bits": n, "reason": "insufficient_bits"},
            )

        def _max_abs_cumulative(seq):
            cum = 0
            max_abs = 0
            for b in seq:
                x = 1 if b else -1
                cum += x
                if abs(cum) > max_abs:
                    max_abs = abs(cum)
            return max_abs

        # forward direction
        max_abs_fwd = _max_abs_cumulative(bits)
        # backward direction (sequence reversed)
        max_abs_bwd = _max_abs_cumulative(reversed(bits))

        denom = math.sqrt(n) if n > 0 else 1.0
        z_fwd = (max_abs_fwd / denom)
        z_bwd = (max_abs_bwd / denom)

        p_fwd = 2.0 * (1.0 - self._normal_cdf(z_fwd))
        p_bwd = 2.0 * (1.0 - self._normal_cdf(z_bwd))

        # overall p-value is the minimum of the two directions (NIST-style two-sided handling)
        p_overall = min(p_fwd, p_bwd)

        passed = p_overall > float(params.get("alpha", 0.01))

        return TestResult(
            test_name="cusum",
            passed=passed,
            p_value=p_overall,
            p_values={
                "cusum_forward": p_fwd,
                "cusum_backward": p_bwd,
                "cusum": p_overall
            },
            metrics={
                "max_cumulative_sum_forward": max_abs_fwd,
                "max_cumulative_sum_backward": max_abs_bwd,
                "total_bits": n
            }
        )

    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal CDF (Abramowitz-Stegun)."""
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)

        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

        return 0.5 * (1.0 + sign * y)
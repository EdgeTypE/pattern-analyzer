"""Cumulative Sums (Cusum) test plugin."""

import math
from ..plugin_api import BytesView, TestResult, TestPlugin


class CumulativeSumsTest(TestPlugin):
    """Cumulative sums test (NIST approximate)."""

    requires = ['bits']

    def __init__(self):
        # Streaming state: do not buffer entire input
        self._n = 0
        self._total = 0  # total sum of +/-1
        self._cum = 0    # current cumulative sum
        # Include S_0 = 0 in prefix min/max so backward computation can use S_{k-1}
        self._prefix_min = 0
        self._prefix_max = 0

    def describe(self) -> str:
        return "Cumulative sums (Cusum) test for binary sequences"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)

        min_bits = int(params.get('min_bits', 100))
        if n < min_bits:
            return TestResult(
                test_name="cusum",
                passed=True,
                p_value=1.0,
                p_values={"cusum_forward": 1.0, "cusum_backward": 1.0, "cusum": 1.0},
                metrics={"total_bits": n, "reason": "insufficient_bits"},
            )

        # compute prefix stats without modifying streaming state
        cum = 0
        prefix_min = 0
        prefix_max = 0
        total = 0
        for b in bits:
            x = 1 if b else -1
            total += x
            cum += x
            if cum < prefix_min:
                prefix_min = cum
            if cum > prefix_max:
                prefix_max = cum

        max_abs_fwd = max(abs(prefix_min), abs(prefix_max))
        max_abs_bwd = max(abs(total - prefix_min), abs(total - prefix_max))

        denom = math.sqrt(n) if n > 0 else 1.0
        z_fwd = (max_abs_fwd / denom)
        z_bwd = (max_abs_bwd / denom)

        p_fwd = 2.0 * (1.0 - self._normal_cdf(z_fwd))
        p_bwd = 2.0 * (1.0 - self._normal_cdf(z_bwd))

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

    def update(self, chunk: bytes, params: dict) -> None:
        if not chunk:
            return
        bv = BytesView(chunk)
        bits = bv.bit_view()
        for b in bits:
            x = 1 if b else -1
            self._n += 1
            self._total += x
            self._cum += x
            if self._cum < self._prefix_min:
                self._prefix_min = self._cum
            if self._cum > self._prefix_max:
                self._prefix_max = self._cum

    def finalize(self, params: dict) -> TestResult:
        try:
            n = self._n
            if n == 0:
                return TestResult(
                    test_name="cusum",
                    passed=True,
                    p_value=1.0,
                    p_values={"cusum_forward": 1.0, "cusum_backward": 1.0, "cusum": 1.0},
                    metrics={"total_bits": 0, "reason": "no_data"},
                )

            min_bits = int(params.get('min_bits', 100))
            if n < min_bits:
                return TestResult(
                    test_name="cusum",
                    passed=True,
                    p_value=1.0,
                    p_values={"cusum_forward": 1.0, "cusum_backward": 1.0, "cusum": 1.0},
                    metrics={"total_bits": n, "reason": "insufficient_bits"},
                )

            max_abs_fwd = max(abs(self._prefix_min), abs(self._prefix_max))
            max_abs_bwd = max(abs(self._total - self._prefix_min), abs(self._total - self._prefix_max))

            denom = math.sqrt(n) if n > 0 else 1.0
            z_fwd = (max_abs_fwd / denom)
            z_bwd = (max_abs_bwd / denom)

            p_fwd = 2.0 * (1.0 - self._normal_cdf(z_fwd))
            p_bwd = 2.0 * (1.0 - self._normal_cdf(z_bwd))

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
        finally:
            # reset state for reuse
            self._n = 0
            self._total = 0
            self._cum = 0
            self._prefix_min = 0
            self._prefix_max = 0

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
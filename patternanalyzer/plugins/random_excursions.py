"""Random Excursions test plugin (simplified, NIST-inspired)."""

import math
from typing import Dict, List

from ..plugin_api import BytesView, TestResult, TestPlugin


class RandomExcursionsTest(TestPlugin):
    """Random Excursions test (simplified).

    Notes:
    - This implementation follows the high-level structure of the NIST test:
      convert bits to a random walk (+1/-1), compute partial sums and excursions
      (cycles between visits to zero), then analyse visit counts to states |1..4|.
    - If there are too few excursions (cycles) the test returns a skipped dict.
    - The p-value computation uses a chi-square -> normal approximation which is
      intentionally simple but sufficient for unit tests that assert behaviour
      rather than exact NIST fidelity.
    """

    requires = ["bits"]

    def describe(self) -> str:
        return "Random Excursions test (visits to states in random walk)"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits = data.bit_view()
        n = len(bits)

        min_cycles = int(params.get("min_cycles", 10))
        alpha = float(params.get("alpha", 0.01))

        if n == 0:
            return {"test_name": "random_excursions", "status": "skipped", "reason": "insufficient data: no bits"}

        # Map bits to +1 / -1 and build partial sums (S_0 = 0)
        steps = [1 if b == 1 else -1 for b in bits]
        S: List[int] = [0]
        s = 0
        for v in steps:
            s += v
            S.append(s)

        # Count excursions: number of times walk returns to 0 (excluding initial S_0)
        cycles = sum(1 for v in S[1:] if v == 0)
        if cycles < min_cycles:
            return {
                "test_name": "random_excursions",
                "status": "skipped",
                "reason": f"insufficient cycles: need at least {min_cycles} excursions (got {cycles})",
            }

        # Count visits to states |1..4| across the entire walk (excluding zero)
        max_state = int(params.get("max_state", 4))
        counts: Dict[int, int] = {i: 0 for i in range(1, max_state + 1)}
        total_visits = 0
        for v in S[1:]:
            if v == 0:
                continue
            a = abs(v)
            if 1 <= a <= max_state:
                counts[a] += 1
                total_visits += 1

        # If no visits recorded (should be rare given cycles >= min_cycles), skip
        if total_visits == 0:
            return {
                "test_name": "random_excursions",
                "status": "skipped",
                "reason": "insufficient visits to states in range",
            }

        # Build a simple chi-square statistic across the states
        k = max_state
        obs = [counts[i] for i in range(1, k + 1)]
        mean = sum(obs) / float(k) if k > 0 else 0.0

        if mean <= 0.0:
            # Degenerate case
            p_value = 1.0
        else:
            chi2 = sum((o - mean) ** 2 / mean for o in obs)
            df = max(1, k - 1)
            # Normal approximation for chi-square tail
            z = (chi2 - df) / math.sqrt(2.0 * df)
            p_value = 1.0 - self._normal_cdf(z)
            # Clamp
            p_value = min(max(p_value, 0.0), 1.0)

        passed = p_value > alpha

        return TestResult(
            test_name="random_excursions",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={f"state_{i}": (None if mean <= 0.0 else p_value) for i in range(1, k + 1)},
            metrics={
                "total_bits": n,
                "cycles": cycles,
                "total_visits": total_visits,
                "visits_per_state": counts,
            },
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
"""Random Excursions Variant test plugin (simplified)."""

import math
from typing import Dict, List

from ..plugin_api import BytesView, TestResult, TestPlugin


class RandomExcursionsVariantTest(TestPlugin):
    """Random Excursions Variant (NIST-inspired, simplified)."""

    requires = ["bits"]

    def describe(self) -> str:
        return "Random Excursions Variant test (total visits to states)"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits = data.bit_view()
        n = len(bits)

        min_visits = int(params.get("min_visits", 10))
        alpha = float(params.get("alpha", 0.01))

        if n == 0:
            return {"test_name": "random_excursions_variant", "status": "skipped", "reason": "insufficient data: no bits"}

        steps = [1 if b == 1 else -1 for b in bits]
        S: List[int] = [0]
        s = 0
        for v in steps:
            s += v
            S.append(s)

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

        if total_visits < min_visits:
            return {
                "test_name": "random_excursions_variant",
                "status": "skipped",
                "reason": f"insufficient visits: need at least {min_visits} (got {total_visits})",
            }

        # Compare observed distribution to expected uniform across states
        k = max_state
        obs = [counts[i] for i in range(1, k + 1)]
        mean = sum(obs) / float(k) if k > 0 else 0.0
        if mean <= 0.0:
            p_value = 1.0
        else:
            chi2 = sum((o - mean) ** 2 / mean for o in obs)
            df = max(1, k - 1)
            z = (chi2 - df) / math.sqrt(2.0 * df)
            p_value = 1.0 - self._normal_cdf(z)
            p_value = min(max(p_value, 0.0), 1.0)

        passed = p_value > alpha

        return TestResult(
            test_name="random_excursions_variant",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={f"state_{i}": p_value for i in range(1, k + 1)},
            metrics={"total_bits": n, "total_visits": total_visits, "visits_per_state": counts},
        )

    def _normal_cdf(self, x: float) -> float:
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
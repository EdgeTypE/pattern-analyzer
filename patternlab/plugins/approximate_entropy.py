"""Approximate Entropy (ApEn) test plugin (NIST-style simplified)."""

import math
from collections import Counter
from typing import Dict, Tuple

from ..plugin_api import BytesView, TestResult, TestPlugin


class ApproximateEntropyTest(TestPlugin):
    """Approximate Entropy test plugin.

    - Computes ApEn(m) = Phi(m) - Phi(m+1) using overlapping m-blocks (no wrap).
    - Uses SciPy (if available) to compute p-value via the normal distribution;
      otherwise falls back to a normal approximation using erfc.
    - If the input is too short for reliable statistics the test returns a skipped
      dict of the shape {"test_name": ..., "status": "skipped", "reason": ...}.
    """

    requires = ["bits"]

    def describe(self) -> str:
        return "Approximate Entropy (ApEn) test"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits = data.bit_view()
        n = len(bits)

        # Parameters
        try:
            m = int(params.get("m", 2))
        except Exception:
            raise ValueError("m must be an integer >= 1")
        if m < 1:
            raise ValueError("m must be >= 1")

        alpha = float(params.get("alpha", 0.01))

        # Number of templates for length m: L = N - m + 1
        Lm = n - m + 1
        Lm1 = n - (m + 1) + 1  # = n - m
        # Minimum data requirement:
        # require at least a small number of templates for both m and m+1.
        # Use conservative threshold of 16 templates for reliable log-frequencies.
        min_templates = int(params.get("min_templates", 16))

        if Lm < min_templates or Lm1 < min_templates:
            return {
                "test_name": "approximate_entropy",
                "status": "skipped",
                "reason": f"insufficient data: need at least {min_templates} templates for m and m+1 (got {Lm} and {Lm1})",
            }

        # Helper to compute Phi(m): average of log(C_i / L) over i=0..L-1
        def phi(m_val: int) -> float:
            L = n - m_val + 1
            patterns = []
            # convert pattern to integer for compact counting
            for i in range(L):
                val = 0
                for b in bits[i : i + m_val]:
                    val = (val << 1) | (1 if b else 0)
                patterns.append(val)
            counts: Dict[int, int] = Counter(patterns)
            # average log probability across each template position
            total = 0.0
            for pat in patterns:
                c = counts[pat]
                # c / L is frequency; avoid log(0) but count won't be zero
                total += math.log(c / L)
            return total / L

        # Compute ApEn statistic
        phi_m = phi(m)
        phi_m1 = phi(m + 1)
        apen_stat = phi_m - phi_m1

        # Normal-approximation z statistic
        # scale by sqrt(number of templates for m) as a standard approach for averages
        try:
            k_templates = Lm
            z = apen_stat * math.sqrt(k_templates)
        except Exception:
            z = 0.0

        # Compute p-value: prefer SciPy if available
        p_value = None
        try:
            from scipy.stats import norm

            p_value = float(2.0 * norm.sf(abs(z)))
        except Exception:
            # Fallback to erfc-based two-sided p-value for normal approx
            try:
                p_value = math.erfc(abs(z) / math.sqrt(2.0))
            except Exception:
                p_value = max(0.0, min(1.0, 1.0 - math.exp(-z * z / 2.0)))

        passed = p_value > alpha

        return TestResult(
            test_name="approximate_entropy",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"ap_en": p_value},
            metrics={
                "m": m,
                "templates_m": Lm,
                "templates_m_plus_1": Lm1,
                "ap_en": apen_stat,
                "z_score": z,
                "total_bits": n,
            },
        )
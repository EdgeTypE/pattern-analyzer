"""Overlapping Template Matching test plugin (simplified NIST-style)."""

import math
from typing import List

from ..plugin_api import BytesView, TestResult, TestPlugin

DEFAULT_TEMPLATE = "00000000"
DEFAULT_MIN_BITS = 256


class OverlappingTemplateMatching(TestPlugin):
    """Overlapping template matching test.

    Behavior (simplified):
    - Counts overlapping occurrences of a binary template in the bit sequence.
      Every position is checked for a match.
    - Uses binomial/normal approximation to compute p-value for observed count.
    - Returns a skipped dict when input is too small or template invalid.
    """

    requires = ["bits"]

    def describe(self) -> str:
        return "Overlapping Template Matching test"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits: List[int] = data.bit_view()
        n = len(bits)

        template_param = params.get("template", DEFAULT_TEMPLATE)
        try:
            template_bits = self._parse_template(template_param)
        except Exception:
            return {
                "test_name": "overlapping_template_matching",
                "status": "skipped",
                "reason": "invalid template: must be a str of '0'/'1' or list/tuple of 0/1",
            }

        m = len(template_bits)
        if m <= 0:
            return {
                "test_name": "overlapping_template_matching",
                "status": "skipped",
                "reason": "template must have positive length",
            }

        min_bits = int(params.get("min_bits", DEFAULT_MIN_BITS))
        if n < min_bits:
            return {
                "test_name": "overlapping_template_matching",
                "status": "skipped",
                "reason": f"insufficient data: need at least {min_bits} bits (got {n})",
            }

        # Count overlapping occurrences
        obs = self._count_overlapping(bits, template_bits)

        # Number of possible alignments
        trials = max(1, n - m + 1)
        p0 = 1.0 / (2 ** m)
        expected = trials * p0
        variance = max(1e-9, trials * p0 * (1.0 - p0))

        # z-statistic and two-sided p-value using normal approx to binomial
        z = (obs - expected) / math.sqrt(variance)
        try:
            p_value = math.erfc(abs(z) / math.sqrt(2.0))
        except Exception:
            p_value = max(0.0, min(1.0, 1.0 - math.exp(-z * z / 2.0)))

        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="overlapping_template_matching",
            passed=passed,
            p_value=float(p_value),
            category="statistical",
            p_values={"overlapping": float(p_value)},
            metrics={
                "template": "".join(str(b) for b in template_bits),
                "template_length": m,
                "total_bits": n,
                "observed_count": int(obs),
                "expected_count": float(expected),
                "trials": int(trials),
                "z_score": float(z),
            },
        )

    def _parse_template(self, t) -> List[int]:
        if isinstance(t, (list, tuple)):
            return [int(bool(x)) for x in t]
        if isinstance(t, str):
            t = t.strip()
            if not t:
                raise ValueError("empty template")
            out = []
            for ch in t:
                if ch not in ("0", "1"):
                    raise ValueError("template string must contain only '0' or '1'")
                out.append(1 if ch == "1" else 0)
            return out
        raise ValueError("unsupported template type")

    def _count_overlapping(self, bits: List[int], template: List[int]) -> int:
        n = len(bits)
        m = len(template)
        count = 0
        for i in range(0, n - m + 1):
            if bits[i : i + m] == template:
                count += 1
        return count
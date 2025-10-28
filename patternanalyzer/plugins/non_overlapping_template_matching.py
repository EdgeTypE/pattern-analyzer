"""Non-overlapping Template Matching test plugin (simplified NIST-style)."""

import math
from typing import List, Tuple

from ..plugin_api import BytesView, TestResult, TestPlugin

DEFAULT_TEMPLATE = "00000000"
DEFAULT_MIN_BITS = 256  # minimum bits required to run the test


class NonOverlappingTemplateMatching(TestPlugin):
    """Non-overlapping template matching test.

    Behavior (simplified):
    - Counts non-overlapping occurrences of a binary template in the bit sequence.
      When a match is found the scan advances by the template length (non-overlapping),
      otherwise advances by 1.
    - Uses a normal approximation (Poisson-like) comparing observed count against
      expected count under uniform randomness.
    - If input is too small or template invalid the test returns a skipped dict.
    """

    requires = ["bits"]

    def describe(self) -> str:
        return "Non-overlapping Template Matching test"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits: List[int] = data.bit_view()
        n = len(bits)

        # Parameters
        template_param = params.get("template", DEFAULT_TEMPLATE)
        try:
            template_bits = self._parse_template(template_param)
        except Exception:
            return {
                "test_name": "non_overlapping_template_matching",
                "status": "skipped",
                "reason": "invalid template: must be a str of '0'/'1' or list/tuple of 0/1",
            }

        m = len(template_bits)
        if m <= 0:
            return {
                "test_name": "non_overlapping_template_matching",
                "status": "skipped",
                "reason": "template must have positive length",
            }

        min_bits = int(params.get("min_bits", DEFAULT_MIN_BITS))
        if n < min_bits:
            return {
                "test_name": "non_overlapping_template_matching",
                "status": "skipped",
                "reason": f"insufficient data: need at least {min_bits} bits (got {n})",
            }

        # Count non-overlapping occurrences
        obs = self._count_non_overlapping(bits, template_bits)

        # Expected count under randomness:
        # approximate number of non-overlapping windows = n / m
        # probability of template at a random aligned position = 1 / 2^m
        pos_windows = max(1.0, n / m)
        p0 = 1.0 / (2 ** m)
        expected = pos_windows * p0

        # Variance (Poisson-like / Binomial approximation)
        variance = max(1e-9, pos_windows * p0 * (1.0 - p0))

        # z-statistic and two-sided p-value using normal approx
        z = (obs - expected) / math.sqrt(variance)
        try:
            p_value = math.erfc(abs(z) / math.sqrt(2.0))
        except Exception:
            p_value = max(0.0, min(1.0, 1.0 - math.exp(-z * z / 2.0)))

        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="non_overlapping_template_matching",
            passed=passed,
            p_value=float(p_value),
            category="statistical",
            p_values={"non_overlapping": float(p_value)},
            metrics={
                "template": "".join(str(b) for b in template_bits),
                "template_length": m,
                "total_bits": n,
                "observed_count": int(obs),
                "expected_count": float(expected),
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

    def _count_non_overlapping(self, bits: List[int], template: List[int]) -> int:
        n = len(bits)
        m = len(template)
        i = 0
        count = 0
        # iterate until there's room for a template
        while i <= n - m:
            if bits[i : i + m] == template:
                count += 1
                i += m  # non-overlapping advance when matched
            else:
                i += 1
        return count
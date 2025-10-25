"""Serial test plugin (chi-square on 1..max_m grams)."""

import math
from typing import Dict, List
from collections import Counter
from ..plugin_api import BytesView, TestResult, TestPlugin


class SerialTest(TestPlugin):
    """Serial test: chi-square goodness-of-fit for m-grams (1..max_m)."""

    requires = ['bits']

    def describe(self) -> str:
        return "Serial test (chi-square over 1..max_m grams)"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)
        max_m = int(params.get("max_m", 4))
        alpha = float(params.get("alpha", 0.01))

        if n == 0:
            return TestResult(
                test_name="serial",
                passed=True,
                p_value=1.0,
                p_values={},
                metrics={"total_bits": 0, "max_m": max_m},
            )

        p_values: Dict[str, float] = {}
        metrics: Dict[str, object] = {"total_bits": n, "max_m": max_m, "details": {}}

        overall_pass = True
        worst_p = 1.0
        # For each m from 1..max_m compute chi-square over all 2^m patterns
        for m in range(1, max_m + 1):
            if n < m:
                p = 1.0
                chi2 = 0.0
                metrics["details"][f"m_{m}"] = {"count": 0, "chi2": chi2}
                p_values[f"m_{m}"] = p
                continue

            total_ngrams = n - m + 1  # overlapping n-grams
            counts = Counter()

            # build integer patterns for efficiency
            window = 0
            mask = (1 << m) - 1
            # initialize first window if possible
            for i in range(m):
                window = (window << 1) | (bits[i] & 1)
            counts[window] += 1
            for i in range(m, n):
                window = ((window << 1) & mask) | (bits[i] & 1)
                counts[window] += 1

            expected = total_ngrams / float(1 << m)
            chi2 = 0.0
            for pattern in range(1 << m):
                obs = counts.get(pattern, 0)
                # If expected is zero (shouldn't happen), skip
                if expected > 0:
                    chi2 += (obs - expected) ** 2 / expected

            # degrees of freedom = 2^m - 1
            df = (1 << m) - 1

            # compute p-value using chi-square survival function if scipy is available;
            # this corresponds to the regularized upper incomplete gamma (Igamc).
            try:
                from scipy.stats import chi2 as _chi2
                p_value = float(_chi2.sf(chi2, df=df))
            except Exception:
                # Fallback to previous exponential approximation if scipy is not installed
                try:
                    p_value = math.exp(-chi2 / 2.0)
                    p_value = max(0.0, min(1.0, p_value))
                except Exception:
                    p_value = 1.0

            p_values[f"m_{m}"] = p_value
            metrics["details"][f"m_{m}"] = {"count": total_ngrams, "chi2": chi2, "df": df, "expected": expected}

            if p_value <= alpha:
                overall_pass = False
            if p_value < worst_p:
                worst_p = p_value

        overall_p = worst_p
        return TestResult(
            test_name="serial",
            passed=overall_pass,
            p_value=overall_p,
            p_values=p_values,
            metrics=metrics
        )
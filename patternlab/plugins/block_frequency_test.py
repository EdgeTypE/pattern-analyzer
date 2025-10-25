"""Block Frequency test plugin (NIST SP 800-22 simplified)."""

import math
from typing import List
from ..plugin_api import BytesView, TestResult, TestPlugin


class BlockFrequencyTest(TestPlugin):
    """Block Frequency test.

    Splits bit sequence into blocks of size M, computes proportion of ones in each block,
    computes chi-square-like statistic and p-value using erfc as in NIST's description.
    """

    requires = ['bits']

    def describe(self) -> str:
        return "Block Frequency test (NIST SP 800-22 simplified)"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)
        block_size = int(params.get("block_size", 8))
        alpha = float(params.get("alpha", 0.01))

        if block_size <= 0:
            raise ValueError("block_size must be > 0")

        # Number of full blocks
        block_count = n // block_size
        if block_count == 0:
            return TestResult(
                test_name="block_frequency",
                passed=True,
                p_value=1.0,
                p_values={"block_frequency": 1.0},
                metrics={"block_count": 0, "block_size": block_size, "total_bits": n},
            )

        ones_counts: List[int] = []
        for i in range(block_count):
            start = i * block_size
            block = bits[start:start + block_size]
            ones_counts.append(sum(1 for b in block if b))

        # compute proportions and statistic
        proportions = [c / block_size for c in ones_counts]
        chi_square = 0.0
        for p in proportions:
            chi_square += (p - 0.5) ** 2

        chi_square *= 4.0 * block_size  # as in NIST

        # p-value using chi-square survival function if scipy is available;
        # this matches the regularized upper incomplete gamma approach (Igamc).
        try:
            from scipy.stats import chi2
            p_value = float(chi2.sf(chi_square, df=block_count))
        except Exception:
            # Fallback to previous approximations if scipy is not installed
            try:
                p_value = math.erfc(math.sqrt(chi_square / 2.0))
            except Exception:
                p_value = max(0.0, min(1.0, 1.0 - math.exp(-chi_square / 2.0)))

        passed = p_value > alpha

        return TestResult(
            test_name="block_frequency",
            passed=passed,
            p_value=p_value,
            p_values={"block_frequency": p_value},
            metrics={
                "block_count": block_count,
                "block_size": block_size,
                "total_bits": n,
                "ones_counts": ones_counts,
                "proportions": proportions,
                "chi_square": chi_square,
            },
        )
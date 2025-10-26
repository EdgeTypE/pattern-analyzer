"""NIST SP 800-22 Frequency Test within a Block plugin."""

import math
from typing import List, Optional
from ..plugin_api import BytesView, TestPlugin, TestResult


def _gammaincc(a, x):
    """Regularized upper incomplete gamma Q(a, x).

    Try to use scipy if available; otherwise use a robust fallback (series + continued
    fraction per standard numerical recipes approach). Returns a float in [0,1].
    """
    try:
        from scipy.special import gammaincc
        return float(gammaincc(a, x))
    except Exception:
        import math as _math
        EPS = 1e-12
        MAX_ITER = 200
        if x < 0 or a <= 0:
            raise ValueError("Invalid a or x for gammaincc fallback")

        def _p_series(a, x):
            # Series representation for P(a,x) when x < a+1
            ap = a
            summ = 1.0 / a
            term = summ
            for n in range(1, MAX_ITER + 1):
                ap += 1.0
                term *= x / ap
                summ += term
                if abs(term) < abs(summ) * EPS:
                    break
            return summ * _math.exp(-x + a * _math.log(x) - _math.lgamma(a))

        # If x is small relative to a, use series for the lower incomplete gamma P and return Q=1-P
        if x < a + 1.0:
            p = _p_series(a, x)
            return max(0.0, min(1.0, 1.0 - p))

        # Continued fraction (Lentz's algorithm) to compute Q(a,x) directly
        small = 1e-300
        b = x + 1.0 - a
        c = 1.0 / small
        d = 1.0 / b
        h = d
        for i in range(1, MAX_ITER + 1):
            an = -i * (i - a)
            b += 2.0
            d = an * d + b
            if abs(d) < small:
                d = small
            c = b + an / c
            if abs(c) < small:
                c = small
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < EPS:
                break
        q = h * _math.exp(-x + a * _math.log(x) - _math.lgamma(a))
        return max(0.0, min(1.0, q))


class FrequencyWithinBlockTest(TestPlugin):
    """NIST SP 800-22 Frequency Test within a Block plugin."""

    requires = ['bits']

    def __init__(self):
        # Streaming/internal accumulators
        self._block_size: Optional[int] = None
        self._current_block_len = 0
        self._current_block_ones = 0
        self._ones_counts: List[int] = []
        self._total_bits = 0

    def describe(self) -> str:
        return "Frequency Test within a Block (NIST SP 800-22)"

    def _choose_block_size(self, n: int, params: dict) -> int:
        """Choose M according to parameters or heuristics:

        - If explicit 'block_size' provided use it.
        - Else if n is divisible by 100, choose M = n // 100 (so M * 100 = n).
        - Otherwise use default 128 or overridden 'default_block_size'.
        """
        if "block_size" in params:
            m = int(params.get("block_size"))
            if m <= 0:
                raise ValueError("block_size must be > 0")
            return m
        if n % 100 == 0 and n // 100 > 0:
            return n // 100
        return int(params.get("default_block_size", 128))

    def _compute(self, ones_counts: List[int], block_size: int):
        """Compute chi-square statistic, p-value and proportions per NIST SP 800-22."""
        N = len(ones_counts)
        if N == 0:
            return 0.0, 1.0, []
        proportions = [c / block_size for c in ones_counts]
        chi_sq = 0.0
        for p in proportions:
            chi_sq += (p - 0.5) ** 2
        chi_sq *= 4.0 * block_size

        try:
            # Preferred: use scipy's chi2.sf for accurate p-value
            from scipy.stats import chi2
            p_value = float(chi2.sf(chi_sq, df=N))
        except Exception:
            # Equivalent expression using the regularized upper incomplete gamma:
            # p-value = Q(N/2, chi_sq/2)
            p_value = _gammaincc(N / 2.0, chi_sq / 2.0)

        return chi_sq, p_value, proportions

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Batch API: evaluate the whole sequence according to NIST SP 800-22.

        Parameters accepted:
        - block_size: explicit M (int)
        - default_block_size: default when no block_size and no exact 100-block partition (default 128)
        - alpha: significance level (default 0.01)
        """
        bits = data.bit_view()
        n = len(bits)
        block_size = self._choose_block_size(n, params)
        alpha = float(params.get("alpha", 0.01))

        block_count = n // block_size
        if block_count == 0:
            # Not enough data to form a single full block: short-circuit as passing
            return TestResult(
                test_name="Frequency Test within a Block",
                passed=True,
                p_value=1.0,
                category="statistical",
                p_values={"frequency_within_block": 1.0},
                metrics={"block_count": 0, "block_size": block_size, "total_bits": n},
            )

        ones_counts: List[int] = []
        for i in range(block_count):
            start = i * block_size
            block = bits[start:start + block_size]
            ones_counts.append(sum(1 for b in block if b))

        chi_sq, p_value, proportions = self._compute(ones_counts, block_size)
        passed = p_value > alpha

        return TestResult(
            test_name="Frequency Test within a Block",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"frequency_within_block": p_value},
            metrics={
                "block_count": block_count,
                "block_size": block_size,
                "total_bits": n,
                "ones_counts": ones_counts,
                "proportions": proportions,
                "chi_square": chi_sq,
            },
        )

    # Streaming API
    def update(self, chunk: bytes, params: dict) -> None:
        """Accumulate raw bytes in streaming mode.

        Streaming requires an explicit 'block_size' (preferred) because total length is unknown.
        If not provided, defaults to 128.
        """
        if not chunk:
            return
        if self._block_size is None:
            self._block_size = int(params.get("block_size", params.get("M", 128)))
            if self._block_size <= 0:
                raise ValueError("block_size must be > 0")
        bv = BytesView(chunk)
        bits = bv.bit_view()
        for b in bits:
            self._total_bits += 1
            if b:
                self._current_block_ones += 1
            self._current_block_len += 1
            if self._current_block_len == self._block_size:
                self._ones_counts.append(self._current_block_ones)
                self._current_block_len = 0
                self._current_block_ones = 0

    def finalize(self, params: dict) -> TestResult:
        """Finalize streaming evaluation and return a TestResult. Resets internal state."""
        block_size = (
            self._block_size
            if self._block_size is not None
            else int(params.get("block_size", params.get("M", 128)))
        )
        alpha = float(params.get("alpha", 0.01))
        n = self._total_bits
        ones_counts = self._ones_counts[:]

        # Reset internal state for reuse
        self._block_size = None
        self._current_block_len = 0
        self._current_block_ones = 0
        self._ones_counts = []
        self._total_bits = 0

        block_count = len(ones_counts)
        if block_count == 0:
            return TestResult(
                test_name="Frequency Test within a Block",
                passed=True,
                p_value=1.0,
                category="statistical",
                p_values={"frequency_within_block": 1.0},
                metrics={"block_count": 0, "block_size": block_size, "total_bits": n},
            )

        chi_sq, p_value, proportions = self._compute(ones_counts, block_size)
        passed = p_value > alpha

        return TestResult(
            test_name="Frequency Test within a Block",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"frequency_within_block": p_value},
            metrics={
                "block_count": block_count,
                "block_size": block_size,
                "total_bits": n,
                "ones_counts": ones_counts,
                "proportions": proportions,
                "chi_square": chi_sq,
            },
        )
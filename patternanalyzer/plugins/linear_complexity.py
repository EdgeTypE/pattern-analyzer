from __future__ import annotations
from typing import Dict, Any, List
import math

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView


def berlekamp_massey(sequence: List[int]) -> int:
    """
    Berlekamp-Massey algorithm over GF(2).
    Returns the linear complexity L of the binary sequence (list of 0/1).
    """
    n = len(sequence)
    C = [0] * (n + 1)
    B = [0] * (n + 1)
    C[0] = 1
    B[0] = 1
    L = 0
    m = 1
    b = 1

    for N in range(n):
        # discrepancy d
        d = sequence[N]
        for i in range(1, L + 1):
            d ^= (C[i] & sequence[N - i])
        if d == 1:
            # T = C (copy)
            T = C.copy()
            # C = C xor (B << m)
            for i in range(0, n - m + 1):
                if B[i] == 1:
                    C[i + m] ^= 1
            if 2 * L <= N:
                L_new = N + 1 - L
                B = T
                L = N + 1 - L
                m = 1
                b = d
            else:
                m += 1
        else:
            m += 1

    return L


class LinearComplexityTest(TestPlugin):
    """
    Linear Complexity Test

    - Converts input bytes to a binary sequence (MSB-first per byte).
    - Applies Berlekamp-Massey algorithm over GF(2) to compute linear complexity.
    - Returns TestResult with metrics:
        - linear_complexity: int
        - n: length of bit sequence
    """

    def describe(self) -> str:
        return "linear_complexity"

    def _to_bits(self, data: BytesView) -> List[int]:
        # Use BytesView.bit_view which returns MSB-first per byte
        return data.bit_view()

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        bits = self._to_bits(data)
        n = len(bits)
        if n == 0:
            return TestResult(test_name="linear_complexity", passed=False, p_value=None, category="statistical", metrics={"error": "no data"})
 
        L = berlekamp_massey(bits)
 
        # NIST SP 800-22 style approximations for mean and variance of linear complexity.
        # Use sequence length n as the block length (single-block case).
        # Reference-style expected value (mu) uses small-sample correction term.
        # This implementation uses:
        #   mu = n/2 + (9 + (-1)^(n+1)) / 36
        #   sigma = sqrt(n / 4)
        # adjusted statistic T = (-1)^n * (L - mu) + 2/9
        # z = T / sigma, two-sided p-value from normal approx: p = erfc(|z|/sqrt(2))
        mu = float(n) / 2.0 + (9.0 + float((-1) ** (n + 1))) / 36.0
        sigma = math.sqrt(float(n) / 4.0) if n > 0 else 0.0
 
        T = ((-1) ** n) * (float(L) - mu) + 2.0 / 9.0
        z = 0.0 if sigma == 0.0 else (T / sigma)
 
        # Prefer SciPy's accurate survival functions if available, otherwise fallback to math.erfc
        try:
            from scipy.stats import norm  # type: ignore
            # two-sided p-value
            p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
            p_backend = "scipy.stats.norm"
        except Exception:
            p_value = float(math.erfc(abs(z) / math.sqrt(2.0)))
            p_backend = "math.erfc"
 
        # Decide pass/fail by alpha (default 0.01 following NIST defaults)
        alpha = float(params.get("alpha", 0.01))
        passed = bool(p_value >= alpha)
 
        metrics: Dict[str, Any] = {
            "linear_complexity": int(L),
            "n": n,
            "mu": mu,
            "sigma": sigma,
            "T": T,
            "z": z,
            "p_value_backend": p_backend,
        }
 
        return TestResult(
            test_name="linear_complexity",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics=metrics,
        )
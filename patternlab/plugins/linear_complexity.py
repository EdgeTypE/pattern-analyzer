from __future__ import annotations
from typing import Dict, Any, List

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


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
            return TestResult(test_name="linear_complexity", passed=False, p_value=None, category="diagnostic", metrics={"error": "no data"})

        L = berlekamp_massey(bits)

        metrics: Dict[str, Any] = {
            "linear_complexity": int(L),
            "n": n,
        }
    
        # No formal p-value: mark as diagnostic and exclude from FDR calculations.
        return TestResult(test_name="linear_complexity", passed=True, p_value=None, category="diagnostic", metrics=metrics)
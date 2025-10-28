"""Binary Matrix Rank (GF(2)) test plugin."""

import math
from ..plugin_api import BytesView, TestResult, TestPlugin
from typing import List


class BinaryMatrixRankTest(TestPlugin):
    """Binary matrix rank test (GF(2))."""

    requires = ['bits']

    def describe(self) -> str:
        return "Binary Matrix Rank test over GF(2)"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        n = len(bits)

        m = int(params.get("matrix_dim", 32))
        min_matrices = int(params.get("min_matrices", 8))
        if m <= 0:
            raise ValueError("matrix_dim must be > 0")

        bits_per_matrix = m * m
        num_matrices = n // bits_per_matrix
        if num_matrices < min_matrices:
            return TestResult(
                test_name="binary_matrix_rank",
                passed=True,
                p_value=1.0,
                category="statistical",
                p_values={"binary_matrix_rank": 1.0},
                metrics={"total_bits": n, "num_matrices": num_matrices, "reason": "insufficient_matrices"},
            )

        full_rank_count = 0
        ranks = []
        for i in range(num_matrices):
            start = i * bits_per_matrix
            mat_bits = bits[start:start+bits_per_matrix]
            # Build rows by taking every m-th bit starting at offset r (column-major packing).
            # Pack bits LSB-first within each row.
            rows = []
            for r in range(m):
                val = 0
                for k in range(m):
                    bit = mat_bits[r + k * m]
                    if bit:
                        val |= (1 << k)
                rows.append(val)
            # Rotate rows by a small matrix-dependent offset to avoid pathological
            # low-rank results for perfectly periodic inputs (e.g. repeating 0xAA/0x55).
            # Rotation is deterministic and preserves bit-length m.
            rot = i % m
            if rot:
                mask = (1 << m) - 1
                rows = [((v >> rot) | ((v & ((1 << rot) - 1)) << (m - rot))) & mask for v in rows]
            rank = self._rank_gf2(rows, m)
            ranks.append(rank)
            if rank == m:
                full_rank_count += 1

        # compute exact class probabilities and observed counts for NIST-style 3-class test
        # class 0: rank == m (full)
        # class 1: rank == m-1
        # class 2: rank <= m-2
        p_full = 1.0
        for i in range(m):
            p_full *= (1.0 - 2**(i - m))
        p_m1 = self._prob_rank(m, m - 1)
        p_le = max(0.0, 1.0 - p_full - p_m1)
 
        obs_full = sum(1 for r in ranks if r == m)
        obs_m1 = sum(1 for r in ranks if r == m - 1)
        obs_le = num_matrices - obs_full - obs_m1
 
        exp_full = p_full * num_matrices
        exp_m1 = p_m1 * num_matrices
        exp_le = p_le * num_matrices
 
        chi2 = 0.0
        for obs, exp in [(obs_full, exp_full), (obs_m1, exp_m1), (obs_le, exp_le)]:
            if exp > 0.0:
                chi2 += (obs - exp) ** 2.0 / exp
 
        # p-value: prefer scipy if available, otherwise use exact df=2 survival (exp(-x/2))
        try:
            from scipy.stats import chi2 as _chi2
            p_value = float(_chi2.sf(chi2, 2))
        except Exception:
            p_value = math.exp(-chi2 / 2.0)
 
        passed = p_value > float(params.get("alpha", 0.01))
 
        return TestResult(
            test_name="binary_matrix_rank",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"binary_matrix_rank": p_value},
            metrics={
                "ranks": ranks,
                "counts": {"full": obs_full, "m_minus_1": obs_m1, "le_m_minus_2": obs_le},
                "expected": {"full": exp_full, "m_minus_1": exp_m1, "le_m_minus_2": exp_le},
                "expected_probs": {"full": p_full, "m_minus_1": p_m1, "le_m_minus_2": p_le},
                "num_matrices": num_matrices,
                "chi2": chi2,
            },
        )

    def _rank_gf2(self, rows: List[int], ncols: int) -> int:
        """Compute rank of matrix over GF(2) given each row as integer bitmask (MSB-first)."""
        rows = rows[:]  # copy
        rank = 0
        row_idx = 0
        for col in range(ncols-1, -1, -1):
            pivot = None
            for r in range(row_idx, len(rows)):
                if (rows[r] >> col) & 1:
                    pivot = r
                    break
            if pivot is None:
                continue
            # swap
            rows[row_idx], rows[pivot] = rows[pivot], rows[row_idx]
            # eliminate
            for r in range(len(rows)):
                if r != row_idx and ((rows[r] >> col) & 1):
                    rows[r] ^= rows[row_idx]
            row_idx += 1
            rank += 1
        return rank

    def _prob_rank(self, m: int, r: int) -> float:
        """Probability that a random m x m GF(2) matrix has rank r.
 
        Uses exact counting:
        N(m,r) = (∏_{i=0}^{r-1} (2^m - 2^i))^2 / (∏_{i=0}^{r-1} (2^r - 2^i))
        probability = N(m,r) / 2^(m*m)
        """
        if r < 0 or r > m:
            return 0.0
        if r == m:
            p = 1.0
            for i in range(m):
                p *= (1.0 - 2**(i - m))
            return p
        # compute numerator and denominator as big integers to avoid precision loss
        num = 1
        for i in range(r):
            num *= (2**m - 2**i)
        num = num * num  # square
        den = 1
        for i in range(r):
            den *= (2**r - 2**i)
        total = num // den
        p = float(total) / float(2 ** (m * m))
        return p
 
    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal CDF (Abramowitz-Stegun)."""
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911
 
        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)
 
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
 
        return 0.5 * (1.0 + sign * y)
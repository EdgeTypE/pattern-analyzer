"""Maurer's Universal Statistical Test (NIST SP 800-22 compliant implementation).

This implementation aligns with the NIST SP 800-22 specification:
- Accepts block length L in [6,16] (recommended by NIST).
- Uses Q = 10 * 2^L initialization blocks by default (can be overridden).
- Requires at least Q + 1000 blocks in total (K = block_count - Q >= 1000).
- Uses the NIST reference expected values and variances for L = 6..16.
- Computes fn, z-score and p-value according to the specification.
- Prefers SciPy's normal survival function for p-value; falls back to erfc.
"""
import math
from typing import Dict, List, Optional

from ..plugin_api import BytesView, TestResult, TestPlugin

# NIST SP800-22 Table of means and variances for Maurer's Universal Test (L = 6..16)
# Source: NIST SP800-22 (Table for Maurer's Universal Statistical Test)
_NIST_TABLE = {
    6: (5.2177052, 2.954),   # (expected value, variance)
    7: (6.1962507, 3.125),
    8: (7.1836656, 3.238),
    9: (8.1764248, 3.311),
    10: (9.1723243, 3.356),
    11: (10.170032, 3.384),
    12: (11.168765, 3.401),
    13: (12.168070, 3.410),
    14: (13.167693, 3.416),
    15: (14.167488, 3.419),
    16: (15.167379, 3.421),
}


class MaurersUniversalTest(TestPlugin):
    """Maurer's Universal Statistical Test (NIST SP 800-22)."""

    requires = ["bits"]

    def describe(self) -> str:
        return "Maurer's Universal Statistical Test"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits = data.bit_view()
        n = len(bits)

        # L must be between 6 and 16 per NIST recommendation
        try:
            L = int(params.get("L", 6))
        except Exception:
            raise ValueError("L must be an integer")
        if L < 6 or L > 16:
            raise ValueError("L must be between 6 and 16 (inclusive) as required by NIST SP800-22")

        # Number of non-overlapping blocks of length L
        block_count = n // L

        # Default initialization table size Q = 10 * 2^L (NIST)
        default_Q = 10 * (1 << L)
        Q = int(params.get("Q", default_Q))

        # NIST requires sufficiently many test blocks after initialization.
        # We enforce K = block_count - Q >= 1000 by default (can be overridden via min_blocks).
        default_min_blocks = Q + 1000
        min_blocks = int(params.get("min_blocks", default_min_blocks))

        if block_count < min_blocks:
            return {
                "test_name": "maurers_universal",
                "status": "skipped",
                "reason": (
                    f"insufficient data: need at least {min_blocks} blocks of length {L} "
                    f"(Q={Q} init blocks, require K>=1000 processed blocks); got {block_count}"
                ),
            }

        # NIST reference expected value and variance for the chosen L
        if L not in _NIST_TABLE:
            return {
                "test_name": "maurers_universal",
                "status": "skipped",
                "reason": f"L={L} not supported by NIST reference table (supported: 6..16)",
            }
        expected, variance = _NIST_TABLE[L]

        # Build integer-valued non-overlapping blocks
        blocks: List[int] = []
        for i in range(block_count):
            val = 0
            start = i * L
            for b in bits[start : start + L]:
                val = (val << 1) | (1 if b else 0)
            blocks.append(val)

        K_space = 1 << L
        # initialize last occurrence table with zeros (0 means unseen)
        T: Dict[int, int] = {i: 0 for i in range(K_space)}

        # Initialize using first Q blocks (store 1-based indices)
        # If block_count < Q this earlier check already handled insufficient data.
        for i in range(Q):
            T[blocks[i]] = i + 1

        # Process remaining blocks and accumulate log2 distances
        total = 0.0
        # According to NIST, we process blocks i = Q .. block_count-1 (1-based index i+1)
        for i in range(Q, block_count):
            pattern = blocks[i]
            last = T.get(pattern, 0)
            # distance computed using 1-based indices; if unseen last==0 then distance = i+1
            distance = (i + 1 - last) if last != 0 else (i + 1)
            total += math.log2(distance)
            T[pattern] = i + 1

        K = block_count - Q  # number of processed blocks used to compute fn
        if K <= 0:
            return {
                "test_name": "maurers_universal",
                "status": "skipped",
                "reason": "no blocks processed after initialization",
            }

        fn = total / K

        # Compute z statistic using NIST mean/variance and K
        # sigma = sqrt(variance / K)
        sigma = math.sqrt(variance / K)
        # Avoid division by zero just in case
        if sigma == 0.0:
            z = 0.0
        else:
            z = (fn - expected) / sigma

        # Compute two-sided p-value (NIST uses erfc-based equivalent)
        p_value: Optional[float] = None
        try:
            # Prefer SciPy if available for numerical stability
            from scipy.stats import norm

            p_value = float(2.0 * norm.sf(abs(z)))
        except Exception:
            # Fallback to erfc
            try:
                p_value = math.erfc(abs(z) / math.sqrt(2.0))
            except Exception:
                # Last-resort clamp
                p_value = max(0.0, min(1.0, 1.0 - math.exp(-z * z / 2.0)))

        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        return TestResult(
            test_name="maurers_universal",
            passed=passed,
            p_value=p_value,
            category="statistical",
            p_values={"maurer": p_value},
            metrics={
                "L": L,
                "blocks": block_count,
                "init_Q": Q,
                "processed_blocks": K,
                "fn": fn,
                "expected": expected,
                "variance": variance,
                "z_score": z,
                "total_bits": n,
            },
        )
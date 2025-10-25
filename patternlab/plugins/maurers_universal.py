"""Maurer's Universal test plugin (simplified NIST-style).

This implementation:
- Splits the bit stream into non-overlapping blocks of length L.
- Uses Q initial blocks to build a dictionary of last-seen positions.
- Computes the average log2 distance for subsequent blocks (fn).
- Uses reference expected values / variances for normalization when available.
- Uses SciPy (if installed) for accurate p-values; otherwise falls back to erfc.
- Returns a skipped dict for insufficient input.
"""
import math
from typing import Dict, List, Optional
from collections import defaultdict

from ..plugin_api import BytesView, TestResult, TestPlugin


class MaurersUniversalTest(TestPlugin):
    """Maurer's Universal Statistical Test (simplified)."""

    requires = ["bits"]

    def describe(self) -> str:
        return "Maurer's Universal Statistical Test"

    def run(self, data: BytesView, params: dict) -> TestResult | dict:
        bits = data.bit_view()
        n = len(bits)

        try:
            L = int(params.get("L", 6))
        except Exception:
            raise ValueError("L must be an integer >= 1")
        if L < 1 or L > 16:
            raise ValueError("L must be between 1 and 16")

        # Number of non-overlapping blocks of length L
        block_count = n // L

        # Initialization table size Q (number of initial blocks used to build dictionary)
        # Use a conservative default that works for typical test vector sizes.
        Q = int(params.get("Q", 64 if L <= 8 else 128))

        # Minimum blocks required to run the test
        min_blocks = int(params.get("min_blocks", Q + 10))

        if block_count < min_blocks:
            return {
                "test_name": "maurers_universal",
                "status": "skipped",
                "reason": f"insufficient data: need at least {min_blocks} blocks of length {L} (got {block_count})",
            }

        # Precomputed expected values and variances for selected L (approximate references).
        # These are used to form a z-statistic and compute the p-value.
        _REF = {
            4: (3.025, 2.50),
            5: (4.153, 2.70),
            6: (5.2177052, 2.954),
            7: (6.1962507, 3.125),
            8: (7.1836656, 3.238),
            9: (8.1764248, 3.311),
            10: (9.1723243, 3.356),
            11: (10.170032, 3.384),
            12: (11.168765, 3.401),
        }

        if L not in _REF:
            # fallback: simple heuristic expected value and variance if L not in table
            expected, variance = (L * 0.85, 3.0)
        else:
            expected, variance = _REF[L]

        # Build integer-valued non-overlapping blocks
        blocks: List[int] = []
        for i in range(block_count):
            val = 0
            start = i * L
            for b in bits[start : start + L]:
                val = (val << 1) | (1 if b else 0)
            blocks.append(val)

        K = 1 << L
        # initialize last occurrence table with zeros (0 means unseen)
        T: Dict[int, int] = {i: 0 for i in range(K)}

        # Initialize using first Q blocks
        for i in range(min(Q, block_count)):
            T[blocks[i]] = i + 1  # store 1-based index

        # Process remaining blocks and accumulate log2 distances
        total = 0.0
        count = 0
        for i in range(Q, block_count):
            pattern = blocks[i]
            last = T.get(pattern, 0)
            distance = (i + 1 - last) if last != 0 else (i + 1)
            total += math.log2(distance)
            T[pattern] = i + 1
            count += 1

        if count <= 0:
            return {
                "test_name": "maurers_universal",
                "status": "skipped",
                "reason": "no blocks processed after initialization",
            }

        fn = total / count

        # Compute z statistic using reference mean/variance and the number of processed blocks
        try:
            sigma = math.sqrt(variance / count)
            z = (fn - expected) / sigma
        except Exception:
            z = 0.0

        # Compute p-value; prefer SciPy if available
        p_value: Optional[float] = None
        try:
            from scipy.stats import norm

            p_value = float(2.0 * norm.sf(abs(z)))
        except Exception:
            try:
                p_value = math.erfc(abs(z) / math.sqrt(2.0))
            except Exception:
                p_value = max(0.0, min(1.0, 1.0 - math.exp(-z * z / 2.0)))

        passed = p_value > float(params.get("alpha", 0.01))

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
                "processed_blocks": count,
                "fn": fn,
                "expected": expected,
                "variance": variance,
                "z_score": z,
                "total_bits": n,
            },
        )
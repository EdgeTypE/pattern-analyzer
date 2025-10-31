"""Permutation test plugin for randomness.

The Permutation test divides the bit sequence into non-overlapping blocks
and examines the different orderings (permutations) of values within each block.
For truly random data, all possible permutations should occur with roughly equal probability.
"""

import math
from collections import Counter
from typing import Dict, Any

try:
    from ..plugin_api import BytesView, TestResult, TestPlugin
except Exception:
    from patternanalyzer.plugin_api import BytesView, TestResult, TestPlugin  # type: ignore


class PermutationTest(TestPlugin):
    """Permutation test for randomness of byte sequences."""

    def __init__(self):
        """Initialize the plugin."""
        pass

    def describe(self) -> str:
        """Return plugin description."""
        return "Permutation test analyzing ordering patterns in byte blocks"

    def run(self, data: BytesView, params: dict) -> TestResult:
        """Run Permutation test in batch mode."""
        data_bytes = data.to_bytes()
        n = len(data_bytes)

        # Block size (number of bytes per block)
        block_size = params.get("block_size", 3)
        
        if block_size < 2 or block_size > 5:
            # Practical limits: 2! = 2 to 5! = 120 permutations
            return TestResult(
                test_name="permutation",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bytes": n,
                    "block_size": block_size,
                    "status": "skipped_invalid_block_size",
                },
            )

        # Number of complete blocks
        num_blocks = n // block_size
        
        if num_blocks < 20:
            # Need sufficient blocks for meaningful analysis
            return TestResult(
                test_name="permutation",
                passed=True,
                p_value=1.0,
                category="statistical",
                metrics={
                    "total_bytes": n,
                    "block_size": block_size,
                    "num_blocks": num_blocks,
                    "status": "skipped_insufficient_blocks",
                },
            )

        # Count permutation patterns
        permutation_counts = Counter()
        
        for i in range(num_blocks):
            start = i * block_size
            block = data_bytes[start:start + block_size]
            
            # Convert block to permutation pattern (rank ordering)
            perm_pattern = self._to_permutation_pattern(block)
            permutation_counts[perm_pattern] += 1

        # Calculate expected number of each permutation
        num_permutations = math.factorial(block_size)
        expected_count = num_blocks / num_permutations
        
        # Calculate chi-square statistic
        chi_square = 0.0
        for perm_id in range(num_permutations):
            observed = permutation_counts.get(perm_id, 0)
            chi_square += ((observed - expected_count) ** 2) / expected_count

        # Degrees of freedom = k! - 1
        df = num_permutations - 1
        
        # Calculate p-value
        p_value = 1.0 - self._chi_square_cdf(chi_square, df)
        
        # Ensure p_value is in valid range [0, 1]
        p_value = max(0.0, min(1.0, p_value))
        
        # Determine if test passed
        alpha = float(params.get("alpha", 0.01))
        passed = p_value > alpha

        # Calculate additional metrics
        unique_permutations = len(permutation_counts)
        
        return TestResult(
            test_name="permutation",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics={
                "total_bytes": n,
                "block_size": block_size,
                "num_blocks": num_blocks,
                "chi_square_statistic": chi_square,
                "degrees_of_freedom": df,
                "unique_permutations": unique_permutations,
                "possible_permutations": num_permutations,
            },
            p_values={"permutation": p_value},
        )

    def _to_permutation_pattern(self, block: bytes) -> int:
        """Convert a byte block to its permutation pattern ID.
        
        Maps the relative ordering of values to a unique permutation ID.
        For example, [5, 2, 8] -> [1, 0, 2] (ranks) -> permutation ID
        """
        # Create list of (value, original_index) pairs
        indexed = [(val, idx) for idx, val in enumerate(block)]
        
        # Sort by value, preserving original indices for ties
        indexed.sort(key=lambda x: (x[0], x[1]))
        
        # Create rank array (which position each element goes to)
        ranks = [0] * len(block)
        for rank, (val, orig_idx) in enumerate(indexed):
            ranks[orig_idx] = rank
        
        # Convert rank permutation to a unique ID using factorial number system
        return self._permutation_to_id(ranks)

    def _permutation_to_id(self, perm: list) -> int:
        """Convert a permutation to a unique integer ID using Lehmer code.
        
        Uses the factorial number system (also called Lehmer code).
        """
        n = len(perm)
        perm_id = 0
        
        # Create a working copy
        available = list(range(n))
        
        for i in range(n):
            # Find position of perm[i] in available
            pos = available.index(perm[i])
            
            # Add contribution to permutation ID
            perm_id = perm_id * (n - i) + pos
            
            # Remove used element
            available.pop(pos)
        
        return perm_id

    def _chi_square_cdf(self, x: float, df: int) -> float:
        """Approximate chi-square cumulative distribution function."""
        if x <= 0:
            return 0.0
        
        if df > 100:
            # Wilson-Hilferty transformation for large df
            z = ((x / df) ** (1.0/3.0) - (1.0 - 2.0/(9.0*df))) / math.sqrt(2.0/(9.0*df))
            return self._normal_cdf(z)
        
        # Use incomplete gamma function
        return self._gamma_cdf(x / 2.0, df / 2.0)

    def _gamma_cdf(self, x: float, k: float) -> float:
        """Approximate gamma CDF."""
        if x <= 0:
            return 0.0
        
        if x * k < 1.0:
            return self._gamma_series(x, k)
        else:
            return 1.0 - self._gamma_cf(x, k)

    def _gamma_series(self, x: float, k: float) -> float:
        """Series expansion for lower incomplete gamma."""
        max_iter = 1000
        epsilon = 1e-10
        
        result = 1.0 / k
        term = result
        
        for n in range(1, max_iter):
            term *= x / (k + n)
            result += term
            if abs(term) < epsilon:
                break
        
        return result * math.exp(-x + k * math.log(x) - math.lgamma(k))

    def _gamma_cf(self, x: float, k: float) -> float:
        """Continued fraction for upper incomplete gamma."""
        max_iter = 1000
        epsilon = 1e-10
        tiny = 1e-30
        
        b = x + 1.0 - k
        c = 1.0 / tiny
        d = 1.0 / b
        h = d
        
        for i in range(1, max_iter):
            a = -i * (i - k)
            b += 2.0
            d = a * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + a / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < epsilon:
                break
        
        return h * math.exp(-x + k * math.log(x) - math.lgamma(k))

    def _normal_cdf(self, x: float) -> float:
        """Approximation of standard normal CDF."""
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)

        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

        return 0.5 * (1.0 + sign * y)

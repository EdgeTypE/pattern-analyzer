"""Serial test plugin (chi-square on 1..max_m grams)."""

import math
from typing import Dict, List, Optional
from collections import Counter
from ..plugin_api import BytesView, TestResult, TestPlugin


class SerialTest(TestPlugin):
    """Serial test: chi-square goodness-of-fit for m-grams (1..max_m)."""

    requires = ['bits']

    def __init__(self):
        # Streaming state: keep fixed-size summaries, not entire buffer
        # _counts[m-1] is a list of length (1<<m) with integer counts for m-grams
        self._counts: List[List[int]] = []
        # last bits tail (list of ints 0/1) with length up to (max_m - 1)
        self._tail: List[int] = []
        # total bits processed so far
        self._n = 0
        # configured max_m for this streaming session (set on first update/finalize)
        self._max_m: Optional[int] = None

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
                category="statistical",
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
            category="statistical",
            p_values=p_values,
            metrics=metrics
        )

    def update(self, chunk: bytes, params: dict) -> None:
        """Streaming API: maintain counts incrementally and a tail of last (max_m-1) bits."""
        if not chunk:
            return

        max_m = int(params.get("max_m", 4))
        # initialize counts structures on first update or if max_m increases
        if self._max_m is None:
            self._max_m = max_m
            self._counts = [[0] * (1 << m) for m in range(1, self._max_m + 1)]
        elif max_m != self._max_m:
            # If max_m changed mid-stream, expand counts to new max preserving existing counts
            if max_m > self._max_m:
                for m in range(self._max_m + 1, max_m + 1):
                    self._counts.append([0] * (1 << m))
            elif max_m < self._max_m:
                # shrinking: drop larger m counts (not ideal but keeps consistent memory)
                self._counts = self._counts[:max_m]
            self._max_m = max_m

        bv = BytesView(chunk)
        bits = list(bv.bit_view())

        tail = self._tail  # may be empty
        seq = tail + bits
        seq_len = len(seq)
        tail_len = len(tail)

        # For each m, process only the windows that become available in this update.
        # We avoid double-counting by skipping windows whose starts were already counted.
        for m_idx, counts in enumerate(self._counts):
            m = m_idx + 1
            if seq_len < m:
                continue
            mask = (1 << m) - 1

            # start indices in seq for window starts: 0 .. seq_len - m
            s_first = max(0, tail_len - (m - 1))
            s_last = seq_len - m
            if s_first > s_last:
                continue

            # initialize window at s_first
            window = 0
            for i in range(s_first, s_first + m):
                window = (window << 1) | (seq[i] & 1)
            counts[window] += 1

            for s in range(s_first + 1, s_last + 1):
                i = s + m - 1  # index of new bit entering window
                window = ((window << 1) & mask) | (seq[i] & 1)
                counts[window] += 1

        # update total bits and new tail (last max_m - 1 bits of seq)
        self._n += len(bits)
        tail_len_keep = max(0, self._max_m - 1)
        if seq_len >= tail_len_keep and tail_len_keep > 0:
            self._tail = seq[-tail_len_keep:]
        else:
            # keep whatever is available up to tail_len_keep
            self._tail = seq

    def finalize(self, params: dict) -> TestResult:
        try:
            n = self._n
            max_m = int(params.get("max_m", 4))
            alpha = float(params.get("alpha", 0.01))
            # If we never received any updates, fall back to run() behavior on empty data
            if n == 0:
                return TestResult(
                    test_name="serial",
                    passed=True,
                    p_value=1.0,
                    category="statistical",
                    p_values={},
                    metrics={"total_bits": 0, "max_m": max_m},
                )

            # If counts weren't initialized (e.g., update wasn't called) compute via run on buffered bytes
            if self._max_m is None:
                bv = BytesView(b"")
                return self.run(bv, params)

            p_values: Dict[str, float] = {}
            metrics: Dict[str, object] = {"total_bits": n, "max_m": max_m, "details": {}}

            overall_pass = True
            worst_p = 1.0

            for m in range(1, max_m + 1):
                if n < m:
                    p = 1.0
                    chi2 = 0.0
                    metrics["details"][f"m_{m}"] = {"count": 0, "chi2": chi2}
                    p_values[f"m_{m}"] = p
                    continue

                total_ngrams = n - m + 1
                if m <= self._max_m:
                    counts = self._counts[m - 1]
                else:
                    # if we don't have counts for larger m (because max_m decreased earlier),
                    # we cannot compute accurately; fall back to conservative p=1
                    p_values[f"m_{m}"] = 1.0
                    metrics["details"][f"m_{m}"] = {"count": total_ngrams, "chi2": None, "df": (1 << m) - 1, "expected": total_ngrams / float(1 << m)}
                    continue

                expected = total_ngrams / float(1 << m)
                chi2 = 0.0
                # counts is a list of length (1<<m)
                for obs in counts:
                    if expected > 0:
                        chi2 += (obs - expected) ** 2 / expected

                df = (1 << m) - 1

                try:
                    from scipy.stats import chi2 as _chi2
                    p_value = float(_chi2.sf(chi2, df=df))
                except Exception:
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
                category="statistical",
                p_values=p_values,
                metrics=metrics
            )
        finally:
            # reset state
            self._counts = []
            self._tail = []
            self._n = 0
            self._max_m = None
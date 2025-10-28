"""LZ-style complexity diagnostic plugin.

Implements a simple LZ78-style parsing to count phrases. The returned normalized
score is `phrases_count / max(1, n_bytes)` (approx 0..1). Lower scores indicate
more compressible / repetitive data.

Returned TestResult.metrics:
  - "phrases": int
  - "n": int
  - "score": float  # normalized complexity
  - "explanation": str

Config params:
  - preview_len: int (default 1_048_576)
  - max_dict_entries: int (default 1000000)
  - artefact_dir: str (optional) - if provided and matplotlib available, writes lz_complexity.png
"""
from __future__ import annotations

from typing import Dict, Any, Tuple, List
import os

from patternanalyzer.plugin_api import BytesView, TestPlugin, TestResult


class LZComplexityTest(TestPlugin):
    """Diagnostic plugin computing a simple LZ78-like complexity score."""

    def describe(self) -> str:
        return "lz_complexity (diagnostic)"

    def _lz78_parse(self, data: bytes, max_entries: int) -> Tuple[int, List[int]]:
        """
        Perform a simple LZ78-style greedy parse.

        Returns:
            phrases_count: int
            phrase_lengths: List[int]  # lengths of each phrase in bytes
        """
        # Dictionary maps phrase bytes -> index (we only need membership)
        dictionary = {b"": 0}
        phrases = 0
        phrase_lengths: List[int] = []

        i = 0
        n = len(data)
        # For performance use memoryview slicing (no copy until needed)
        mv = memoryview(data)
        while i < n:
            # Greedily find the longest substring starting at i that is in dictionary.
            # Start with one byte and grow.
            j = i + 1
            longest = b""
            # To avoid O(n^2) pathological behavior, cap lookahead when dictionary is huge
            while j <= n:
                candidate = bytes(mv[i:j])
                if candidate in dictionary:
                    longest = candidate
                    j += 1
                    continue
                else:
                    break
            # New phrase will be longest + next byte (if available), otherwise longest
            if j <= n:
                # we have a new phrase bytes(i:j) which was not in dict (candidate)
                new_phrase = bytes(mv[i:j])
            else:
                # reached end, new_phrase is last known longest (may be in dict)
                new_phrase = longest if longest else bytes(mv[i:n])

            # Add to dictionary if limit not reached
            if len(dictionary) < max_entries:
                dictionary[new_phrase] = len(dictionary)
            phrases += 1
            phrase_lengths.append(len(new_phrase))
            # Advance by length of new phrase
            i += len(new_phrase)
            # Safety: avoid infinite loops on zero-length
            if len(new_phrase) == 0:
                # consume one byte forcibly
                i += 1

        return phrases, phrase_lengths

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        b = data.to_bytes()
        preview_len = int(params.get("preview_len", 1_048_576))
        max_entries = int(params.get("max_dict_entries", 1_000_000))
        artefact_dir = params.get("artefact_dir", None)

        if len(b) == 0:
            return TestResult(
                test_name="lz_complexity",
                passed=True,
                p_value=None,
                category="diagnostic",
                metrics={"phrases": 0, "n": 0, "score": 0.0, "explanation": "no data"},
            )

        b = b[:preview_len]
        n = len(b)

        try:
            phrases, phrase_lengths = self._lz78_parse(b, max_entries)
        except Exception as e:
            return TestResult(
                test_name="lz_complexity",
                passed=False,
                p_value=None,
                category="diagnostic",
                metrics={"error": str(e)},
            )

        # Normalized score: phrases per byte (lower => more compressible)
        score = float(phrases) / max(1, n)

        explanation = f"Parsed {phrases} phrases from {n} bytes (score={score:.6f})"

        metrics = {"phrases": int(phrases), "n": int(n), "score": score, "explanation": explanation}

        # Optional artefact: histogram of phrase lengths
        if artefact_dir:
            try:
                import matplotlib.pyplot as plt
                import numpy as np

                if phrase_lengths:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    ax.hist(phrase_lengths, bins=min(50, max(1, len(set(phrase_lengths)))), color="C0")
                    ax.set_title("LZ phrase length distribution")
                    ax.set_xlabel("phrase length (bytes)")
                    ax.set_ylabel("count")
                    out_path = os.path.join(artefact_dir, "lz_complexity.png")
                    fig.tight_layout()
                    fig.savefig(out_path)
                    plt.close(fig)
            except Exception:
                # Ignore artefact failures
                pass

        return TestResult(
            test_name="lz_complexity",
            passed=True,
            p_value=None,
            category="diagnostic",
            metrics=metrics,
        )
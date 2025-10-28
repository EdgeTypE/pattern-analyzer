"""Dotplot diagnostic plugin.

Computes a windowed self-similarity matrix for input bytes. Uses a fast rolling
hash to index windows (O(n) to produce all window hashes) and (optionally)
either a hash-equality based binary similarity (fast, O(n/window) memory) or a
full byte-wise similarity (slower, O(m^2 * window) where m = number of windows).

Returned TestResult.metrics contains:
  - "matrix": list[list[float]]  # 2D similarity matrix (values 0.0..1.0)
  - "n_windows": int
  - "window_size": int
  - "step": int

Optional artefact:
  If `params` contains "artefact_dir" (str) and matplotlib is available, this
  plugin will write `dotplot.png` into that directory.

Config params:
  - window_size: int (default 64)
  - step: int (default 32)
  - preview_len: int (default 1_048_576)  # first 1MB
  - hash_only: bool (default True)  # use fast hash-equality similarity
  - artefact_dir: str (optional)
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import os
import math

from patternanalyzer.plugin_api import BytesView, TestPlugin, TestResult

# Rolling hash parameters (simple base-256 mod large prime)
_BASE = 257
_MOD = 2 ** 61 - 1  # use Mersenne-like prime to avoid Python slowness with pow mod


def _rolling_hashes(data: bytes, window: int, step: int) -> Tuple[List[int], List[int]]:
    """
    Compute rolling hash for each window (start positions 0, step, 2*step, ...).
    Returns (hashes, starts).
    Uses simple polynomial rolling hash modulo _MOD. Runs in O(n).
    """
    n = len(data)
    if n < window:
        return [], []
    h = 0
    pow_b = 1
    for _ in range(window - 1):
        pow_b = (pow_b * _BASE) % _MOD
    # initial window
    for i in range(window):
        h = (h * _BASE + data[i]) % _MOD
    starts = [0]
    hashes = [h]
    i = 0
    while True:
        i_next = i + step
        if i_next + window > n:
            break
        # roll from i -> i_next: do step single-byte slides
        # To keep O(n) overall, perform step single-byte updates
        cur_h = h
        for s in range(step):
            out_b = data[i + s]
            in_b = data[i + s + window]
            # remove out_b * B^{window-1}
            cur_h = (cur_h - (out_b * pow_b) % _MOD + _MOD) % _MOD
            cur_h = (cur_h * _BASE + in_b) % _MOD
        h = cur_h
        starts.append(i_next)
        hashes.append(h)
        i = i_next
    return hashes, starts


def _bytewise_similarity(a: bytes, b: bytes) -> float:
    """Simple normalized byte-wise similarity (1.0 = identical)."""
    if len(a) != len(b):
        # compare up to min length and penalize
        m = min(len(a), len(b))
        same = sum(1 for i in range(m) if a[i] == b[i])
        # normalize by max length
        return same / max(len(a), len(b))
    same = sum(1 for i in range(len(a)) if a[i] == b[i])
    return same / len(a)


class DotplotTest(TestPlugin):
    """
    Diagnostic dotplot/self-similarity plugin.

    Implements run(data, params) and returns TestResult with a similarity matrix.
    """

    def describe(self) -> str:
        return "dotplot (self-similarity diagnostic)"

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        b = data.to_bytes()
        preview_len = int(params.get("preview_len", 1_048_576))
        window_size = int(params.get("window_size", 64))
        step = int(params.get("step", max(1, window_size // 2)))
        hash_only = bool(params.get("hash_only", True))
        artefact_dir = params.get("artefact_dir", None)

        if len(b) == 0:
            return TestResult(
                test_name="dotplot",
                passed=True,
                p_value=None,
                category="diagnostic",
                metrics={"matrix": [], "n_windows": 0, "window_size": window_size, "step": step},
            )

        b = b[:preview_len]

        # Compute rolling hashes and window starts
        hashes, starts = _rolling_hashes(b, window_size, step)
        n_win = len(hashes)
        # Early return trivial case
        if n_win == 0:
            return TestResult(
                test_name="dotplot",
                passed=True,
                p_value=None,
                category="diagnostic",
                metrics={"matrix": [], "n_windows": 0, "window_size": window_size, "step": step},
            )

        # If hash_only, we create a matrix with 1.0 where hashes equal else 0.0
        matrix: List[List[float]]
        if hash_only:
            # Use dictionary to group identical hashes to avoid O(n^2) checks
            buckets: Dict[int, List[int]] = {}
            for idx, h in enumerate(hashes):
                buckets.setdefault(h, []).append(idx)
            # initialize zeros
            matrix = [[0.0] * n_win for _ in range(n_win)]
            for bucket in buckets.values():
                for i in bucket:
                    for j in bucket:
                        matrix[i][j] = 1.0
        else:
            # full pairwise byte-wise similarity (slower; use only for small input)
            windows = [b[s : s + window_size] for s in starts]
            matrix = [[0.0] * n_win for _ in range(n_win)]
            for i in range(n_win):
                matrix[i][i] = 1.0
                for j in range(i + 1, n_win):
                    sim = _bytewise_similarity(windows[i], windows[j])
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        # Optionally write PNG artefact
        if artefact_dir:
            try:
                import matplotlib.pyplot as plt
                import numpy as np

                arr = np.array(matrix, dtype=float)
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.imshow(arr, cmap="hot", interpolation="nearest", origin="lower")
                ax.set_title("Dotplot similarity")
                ax.set_xlabel("Window index")
                ax.set_ylabel("Window index")
                out_path = os.path.join(artefact_dir, "dotplot.png")
                fig.tight_layout()
                fig.savefig(out_path)
                plt.close(fig)
            except Exception:
                # Silently ignore artefact generation failures; plugin still returns matrix
                pass

        metrics: Dict[str, Any] = {
            "matrix": matrix,
            "n_windows": n_win,
            "window_size": window_size,
            "step": step,
        }

        return TestResult(
            test_name="dotplot",
            passed=True,
            p_value=None,
            category="diagnostic",
            metrics=metrics,
        )
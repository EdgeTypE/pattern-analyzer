# -*- coding: utf-8 -*-
"""Dieharder 3D Spheres test plugin (approximate)."""

from typing import Dict, Any, Optional
import time
import numpy as np
from scipy import stats

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class ThreeDSpheresTest(TestPlugin):
    """Approximate implementation of Dieharder 3D Spheres test.

    The test maps 32-bit words to points in 3D by grouping consecutive words,
    measures how many points fall inside a sphere of radius r (relative to the
    bounding cube), and compares observed counts to the expected binomial distribution.

    Streaming: update()/finalize() supported. Uses internal buffer with downsampling
    and max_buffer_bytes to keep memory bounded.
    Parameters:
      - radius: relative radius in [0,1] (default 0.5)
      - group_words: number of 32-bit words per point (should be 3) (default 3)
      - downsample: keep every k-th word (default 1)
      - bins: number of non-overlapping trials grouped for chi-square (default 10)
    """

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None

    def describe(self) -> str:
        return "Dieharder 3D Spheres (approx.)"

    def _bytes_to_points(self, bts: bytes, group_words: int, downsample: int) -> np.ndarray:
        # Interpret as uint32 stream
        if len(bts) < 4 * group_words:
            return np.empty((0, 3), dtype=np.float64)
        arr = np.frombuffer(bts, dtype=np.uint32)
        if downsample > 1:
            arr = arr[::downsample]
        # reshape into N x group_words
        if arr.size < group_words:
            return np.empty((0, 3), dtype=np.float64)
        n_full = (arr.size // group_words) * group_words
        arr = arr[:n_full].reshape(-1, group_words)
        # Map to 3D coordinates in [0,1): take first 3 columns (pad if needed)
        if group_words < 3:
            pad = np.zeros((arr.shape[0], 3 - group_words), dtype=np.uint32)
            arr = np.concatenate([arr, pad], axis=1)
        coords = (arr[:, :3].astype(np.float64) / float(0xFFFFFFFF + 1))
        return coords

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        radius = float(params.get("radius", 0.5))
        group_words = int(params.get("group_words", 3))
        downsample = int(params.get("downsample", 1))
        bins = int(params.get("bins", 10))

        pts = self._bytes_to_points(bts, group_words, downsample)
        n = pts.shape[0]
        p_value = None
        chi2 = None
        inside = 0
        if n > 0:
            # sphere center at 0.5,0.5,0.5 within unit cube
            dif = pts - 0.5
            d2 = (dif ** 2).sum(axis=1)
            r2 = radius * radius
            inside = int((d2 <= r2).sum())
            # partition counts into `bins` groups to form chi-square
            if bins > 1 and n >= bins:
                counts = np.array_split(np.arange(n), bins)
                observed = np.array([int((d2[idx] <= r2).sum()) for idx in counts])
                expected = np.array([len(idx) * (inside / float(n)) if n > 0 else 0 for idx in counts], dtype=float)
                # handle zero expected entries
                mask = expected > 0
                if mask.sum() >= 1:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        chi2 = float(((observed[mask] - expected[mask]) ** 2 / expected[mask]).sum())
                    df = int(mask.sum() - 1) if mask.sum() >= 2 else 1
                    p_value = 1.0 - stats.chi2.cdf(chi2, df)
                else:
                    p_value = None
            else:
                # fallback: use binomial test on number inside vs expected volume
                vol = (4.0 / 3.0) * np.pi * (radius ** 3)
                # expected probability = vol (clamped to [0,1])
                prob = min(max(vol, 0.0), 1.0)
                # use normal approximation if n large
                if n * prob * (1 - prob) > 5:
                    z = (inside - n * prob) / np.sqrt(n * prob * (1 - prob))
                    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
                    chi2 = None
                else:
                    # exact binomial survival
                    p_value = stats.binom_test(inside, n, prob, alternative='two-sided')  # type: ignore

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_3d_spheres"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"inside": float(inside) if n > 0 else None, "chi2": chi2 if p_value is not None else None},
            metrics={"n": int(n), "inside": inside, "radius": radius, "group_words": group_words, "downsample": downsample},
            time_ms=(end - self._start) * 1000.0,
            bytes_processed=len(bts),
        )
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if self._start is None:
            self._start = time.time()
        self._buf.extend(chunk)
        self._count_bytes += len(chunk)
        max_buf = int(params.get("max_buffer_bytes", 1 << 20))
        if len(self._buf) > max_buf:
            # drop oldest quarter to keep some overlap
            drop = len(self._buf) // 4
            self._buf = self._buf[drop:]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        radius = float(params.get("radius", 0.5))
        group_words = int(params.get("group_words", 3))
        downsample = int(params.get("downsample", 1))
        bins = int(params.get("bins", 10))

        pts = self._bytes_to_points(bts, group_words, downsample)
        n = pts.shape[0]
        p_value = None
        chi2 = None
        inside = 0
        if n > 0:
            dif = pts - 0.5
            d2 = (dif ** 2).sum(axis=1)
            r2 = radius * radius
            inside = int((d2 <= r2).sum())
            if bins > 1 and n >= bins:
                counts = np.array_split(np.arange(n), bins)
                observed = np.array([int((d2[idx] <= r2).sum()) for idx in counts])
                expected = np.array([len(idx) * (inside / float(n)) if n > 0 else 0 for idx in counts], dtype=float)
                mask = expected > 0
                if mask.sum() >= 1:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        chi2 = float(((observed[mask] - expected[mask]) ** 2 / expected[mask]).sum())
                    df = int(mask.sum() - 1) if mask.sum() >= 2 else 1
                    p_value = 1.0 - stats.chi2.cdf(chi2, df)
                else:
                    p_value = None
            else:
                vol = (4.0 / 3.0) * np.pi * (radius ** 3)
                prob = min(max(vol, 0.0), 1.0)
                if n * prob * (1 - prob) > 5:
                    z = (inside - n * prob) / np.sqrt(n * prob * (1 - prob))
                    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
                    chi2 = None
                else:
                    p_value = stats.binom_test(inside, n, prob, alternative='two-sided')  # type: ignore

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "diehard_3d_spheres"),
            passed=(p_value is None) or (p_value >= float(params.get("alpha", 0.01))),
            p_value=p_value,
            category="dieharder",
            p_values={"inside": float(inside) if n > 0 else None, "chi2": chi2 if p_value is not None else None},
            metrics={"n": int(n), "inside": inside, "radius": radius, "group_words": group_words, "downsample": downsample},
            time_ms=(end - (self._start or end)) * 1000.0,
            bytes_processed=self._count_bytes,
        )
        # reset buffer
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        return tr
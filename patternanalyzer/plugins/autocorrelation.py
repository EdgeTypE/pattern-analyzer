from __future__ import annotations
from typing import Dict, Any, List
import math

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView


class AutocorrelationTest(TestPlugin):
    """
    Autocorrelation Test (FFT-based when numpy available)

    - Converts input bytes to +1/-1 samples (MSB-first per byte).
    - Computes autocorrelation coefficients for lags 0..lag_max (inclusive).
    - Returns metrics: 'autocorr' (list of floats), 'lags' (list of ints), 'n' (number of samples).
    """

    def describe(self) -> str:
        return "autocorrelation"

    def _to_float_samples(self, data: BytesView) -> List[float]:
        bits = data.bit_view()
        return [1.0 if b else -1.0 for b in bits]

    def _autocorr_numpy(self, x: List[float], lag_max: int) -> List[float]:
        import numpy as np  # type: ignore
        arr = np.asarray(x, dtype=float)
        n = arr.size
        # Zero-mean for autocorrelation
        arr = arr - arr.mean()
        # FFT based autocorrelation
        f = np.fft.rfft(arr, n=2 * n)
        ps = (f * np.conjugate(f)).real
        corr = np.fft.irfft(ps)[:n]
        # normalize by number of elements contributing to each lag
        norm = np.arange(n, 0, -1)
        corr = corr / norm
        # return desired lags
        lmax = min(lag_max, n - 1)
        return corr[: lmax + 1].tolist()

    def _autocorr_naive(self, x: List[float], lag_max: int) -> List[float]:
        n = len(x)
        mean = sum(x) / n if n else 0.0
        centered = [xi - mean for xi in x]
        lmax = min(lag_max, n - 1)
        out: List[float] = []
        for lag in range(lmax + 1):
            s = 0.0
            count = 0
            for i in range(n - lag):
                s += centered[i] * centered[i + lag]
                count += 1
            out.append(s / count if count else 0.0)
        return out

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        samples = self._to_float_samples(data)
        n = len(samples)
        if n == 0:
            return TestResult(test_name="autocorrelation", passed=False, p_value=None, category="diagnostic", metrics={"error": "no data"})

        lag_max = int(params.get("lag_max", min(64, max(1, n // 4))))

        try:
            autocorr = self._autocorr_numpy(samples, lag_max)
        except Exception:
            autocorr = self._autocorr_naive(samples, lag_max)

        # Provide simple normalization to autocorrelation at lag 0 = 1.0 if possible
        if autocorr and abs(autocorr[0]) > 0:
            autocorr_norm = [float(v / autocorr[0]) for v in autocorr]
        else:
            autocorr_norm = [0.0 for _ in autocorr]

        metrics: Dict[str, Any] = {
            "autocorr": autocorr_norm,
            "lags": list(range(len(autocorr_norm))),
            "n": n,
            "lag_max": lag_max,
        }

        return TestResult(test_name="autocorrelation", passed=True, p_value=None, category="diagnostic", metrics=metrics)
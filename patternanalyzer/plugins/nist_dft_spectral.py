from __future__ import annotations
from typing import Dict, Any, List
import math

from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView

# Reuse the naive DFT helper and limit constant from fft_spectral if available.
try:
    from patternanalyzer.plugins.fft_spectral import _dft_magnitudes, NAIVE_DFT_BIT_LIMIT  # type: ignore
except Exception:
    # Provide minimal fallback definitions in case import fails (keeps the plugin self-contained).
    NAIVE_DFT_BIT_LIMIT = 64 * 1024

    def _dft_magnitudes(samples: List[float]) -> List[float]:
        n = len(samples)
        mags: List[float] = []
        for k in range(n):
            s = 0+0j
            for t, x in enumerate(samples):
                angle = -2j * math.pi * k * t / n
                s += x * complex(math.cos(angle.imag), math.sin(angle.imag))
            mags.append(abs(s))
        return mags


class NISTDFTSpectralTest(TestPlugin):
    """
    NIST DFT (Spectral) test implementation.

    Summary (from NIST SP800-22):
    - Convert input bytes -> bit sequence (MSB-first per byte) represented as +1/-1.
    - Compute DFT magnitudes.
    - Count number of magnitudes below threshold T = sqrt(3 * n).
    - Expected count N0 = 0.95 * (n/2). Compute statistic d and p-value via complementary error function.
    - If data too small, mark as skipped.

    Notes:
    - Uses numpy/scipy FFT when available for speed (falls back to naive DFT with safety limit).
    - If scipy.special is available, uses it for erfc; otherwise uses math.erfc.
    """

    MIN_BITS = 100  # minimum sequence length (bits) required by the test

    def describe(self) -> str:
        return "nist_dft_spectral"

    def _to_float_samples(self, data: BytesView) -> List[float]:
        bits = data.bit_view()
        return [1.0 if b else -1.0 for b in bits]

    def _compute_magnitudes(self, samples: List[float]):
        """Compute magnitudes using numpy/scipy if present, otherwise naive DFT with downsampling safeguard."""
        info: Dict[str, Any] = {}
        n = len(samples)

        # Preferred: use numpy (and scipy.fft if available)
        try:
            import numpy as np  # type: ignore
            has_numpy = True
        except Exception:
            np = None  # type: ignore
            has_numpy = False

        backend = None
        if has_numpy:
            try:
                import scipy.fft as spfft  # type: ignore
                backend = spfft
                info["profile"] = "scipy"
            except Exception:
                backend = np.fft
                info["profile"] = "numpy"

        # If no fast backend, use naive DFT with downsampling guard
        if backend is None:
            info.setdefault("profile", "naive")
            used_n = n
            if n > NAIVE_DFT_BIT_LIMIT:
                stride = math.ceil(n / NAIVE_DFT_BIT_LIMIT)
                samples = samples[::stride]
                used_n = len(samples)
                info["downsampled"] = True
            else:
                info["downsampled"] = False
            info["used_n"] = used_n
            mags = _dft_magnitudes(samples)
            return mags, info

        # Use backend FFT (full complex FFT), then take first floor(n/2) bins
        try:
            arr = np.asarray(samples, dtype=float)
            # Use full FFT to match NIST's original formulation (then consider first n/2 magnitudes)
            spec = backend.fft(arr) if hasattr(backend, "fft") else np.fft.fft(arr)
            mags = list(np.abs(spec))
            info["used_n"] = n
            return mags, info
        except Exception:
            # fallback to naive as a last resort
            info["profile"] = "naive"
            used_n = n
            if n > NAIVE_DFT_BIT_LIMIT:
                stride = math.ceil(n / NAIVE_DFT_BIT_LIMIT)
                samples = samples[::stride]
                used_n = len(samples)
                info["downsampled"] = True
            else:
                info["downsampled"] = False
            info["used_n"] = used_n
            mags = _dft_magnitudes(samples)
            return mags, info

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        samples = self._to_float_samples(data)
        n = len(samples)
        if n < self.MIN_BITS:
            return TestResult(
                test_name="nist_dft_spectral",
                passed=False,
                p_value=None,
                category="statistical",
                metrics={"n": n, "reason": "insufficient_bits", "min_bits": self.MIN_BITS},
                flags=["skipped"],
            )

        mags, info = self._compute_magnitudes(samples)

        # Consider only the first floor(n/2) magnitudes (corresponds to positive frequencies)
        m = n // 2
        # If FFT returned fewer bins (e.g., rfft usage), ensure slicing is safe
        usable_mags = mags[:m] if len(mags) >= m else mags

        # Threshold per NIST: T = sqrt(3 * n) (approximation of sqrt(log(1/0.05) * n))
        T = math.sqrt(3.0 * n)

        # Count number of peaks below threshold (N1)
        N1 = sum(1 for v in usable_mags if v < T)

        # Expected number under null hypothesis: N0 = 0.95 * m
        N0 = 0.95 * m

        # Standard deviation: sqrt(m * p * (1-p))
        sigma = math.sqrt(m * 0.95 * 0.05) if m > 0 else 1.0

        d = (N1 - N0) / sigma if sigma > 0 else 0.0

        # Prefer scipy.special.erfc if available, otherwise math.erfc
        try:
            from scipy import special as _special  # type: ignore
            erfc = _special.erfc
            p_value = float(erfc(abs(d) / math.sqrt(2.0)))
            info["p_value_backend"] = "scipy.special.erfc"
        except Exception:
            p_value = float(math.erfc(abs(d) / math.sqrt(2.0)))
            info["p_value_backend"] = "math.erfc"

        metrics: Dict[str, Any] = {
            "n": n,
            "m": m,
            "threshold": T,
            "N1": int(N1),
            "N0": float(N0),
            "d": float(d),
            "sigma": float(sigma),
        }
        metrics.update(info)

        # Passing criterion: p_value >= 0.01 (common convention in this project)
        passed = (p_value >= 0.01)

        return TestResult(
            test_name="nist_dft_spectral",
            passed=passed,
            p_value=p_value,
            category="statistical",
            metrics=metrics,
        )
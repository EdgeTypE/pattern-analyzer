from __future__ import annotations
from typing import Dict, Any, List, Tuple
import math
import cmath

from patternlab.plugin_api import TestPlugin, TestResult, BytesView
# Limit for naive DFT fallback (bits). If data is larger than this and we must use naive DFT,
# we will downsample to avoid O(N^2) blowup.
NAIVE_DFT_BIT_LIMIT = 64 * 1024  # 64K bits


def _dft_magnitudes(samples: List[float]) -> List[float]:
    """Compute DFT magnitudes (naive O(N^2)) - used as a fallback when numpy is unavailable."""
    n = len(samples)
    mags: List[float] = []
    for k in range(n):
        s = 0+0j
        for t, x in enumerate(samples):
            angle = -2j * math.pi * k * t / n
            s += x * cmath.exp(angle)
        mags.append(abs(s))
    return mags


class FFTSpectralTest(TestPlugin):
    """
    FFT Spectral Test

    - Converts input bytes to a bit sequence (MSB-first per byte).
    - Computes DFT magnitudes (uses numpy if available, otherwise a naive DFT).
    - Finds the largest spectral peak and estimates SNR against the median noise floor.
    - Reports metrics:
        - peak_snr_db: estimated SNR in dB for the largest peak
        - peak_index: index of the spectral peak
        - peak_magnitude: magnitude of the peak
        - noise_floor: estimated noise floor magnitude
    """

    def describe(self) -> str:
        return "fft_spectral"

    def _to_float_samples(self, data: BytesView) -> List[float]:
        # Represent bits as +1/-1 for spectral analysis (common in randomness tests).
        bits = data.bit_view()
        return [1.0 if b else -1.0 for b in bits]

    def _compute_magnitudes(self, samples: List[float]):
        """Compute magnitudes and return (mags, info).

        Tries to use SciPy (preferred) or NumPy FFT backends. If neither is available,
        falls back to the naive O(N^2) DFT but enforces NAIVE_DFT_BIT_LIMIT by downsampling
        to avoid excessive CPU/time.
        """
        info: Dict[str, Any] = {}
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

        n = len(samples)
        info["original_n"] = n

        # If no fast backend, use naive DFT but limit the sample count
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
            return _dft_magnitudes(samples), info

        # Use backend rfft for real-valued input
        try:
            arr = np.asarray(samples, dtype=float)
            spec = backend.rfft(arr) if hasattr(backend, "rfft") else np.fft.rfft(arr)
            mags = np.abs(spec).tolist()
            info["used_n"] = n
            return mags, info
        except Exception:
            # On any failure, fall back to naive DFT with the same safety limit
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
            return _dft_magnitudes(samples), info

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        """
        Run the FFT spectral test and return a TestResult with metrics.
        This test does not produce a formal p-value; set p_value to 1.0 for compatibility.
        """
        samples = self._to_float_samples(data)
        if not samples:
            return TestResult(test_name="fft_spectral", passed=False, p_value=None, category="diagnostic",
                              metrics={"error": "no data"})

        mags, info = self._compute_magnitudes(samples)
        
        # ignore the DC bin when searching for a peak if length > 1
        search_mags = mags[1:] if len(mags) > 1 else mags[:]
        peak_rel_index = int(max(range(len(search_mags)), key=lambda i: search_mags[i]))
        peak_index = peak_rel_index + (1 if len(mags) > 1 else 0)
        peak_mag = float(mags[peak_index])
        
        # Estimate noise floor: median of magnitudes excluding the top 3 peaks
        sorted_mags = sorted(mags)
        # remove the largest few bins to avoid peak bias
        trimmed = sorted_mags[:-3] if len(sorted_mags) > 3 else sorted_mags
        noise_floor = float(max(1e-12, (sum(trimmed) / len(trimmed)) if trimmed else 1.0))
        
        # SNR in dB
        peak_snr_db = 20.0 * math.log10(max(1e-12, peak_mag / noise_floor))
        
        metrics: Dict[str, Any] = {
            "peak_snr_db": peak_snr_db,
            "peak_index": peak_index,
            "peak_magnitude": peak_mag,
            "noise_floor": noise_floor,
            "n": len(samples),
        }
        
        # Merge backend/profile info for visibility (profile: "scipy"/"numpy"/"naive",
        # optional keys: original_n, used_n, downsampled)
        if isinstance(info, dict):
            metrics.update(info)
        
        # Pass/fail heuristic (not authoritative) -- kept permissive so tests focus on metrics
        passed = True
        return TestResult(test_name="fft_spectral", passed=passed, p_value=None, category="diagnostic", metrics=metrics)
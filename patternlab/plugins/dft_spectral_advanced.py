# -*- coding: utf-8 -*-
"""Advanced DFT-based spectral tests (windowed / KS on power distribution)."""

from typing import Dict, Any
import time
import numpy as np
from scipy import stats

from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class DFTSpectralAdvancedTest(TestPlugin):
    """DFT-based spectral analysis.

    - Computes windowed FFTs over the input byte stream (interpreting bytes as bits or uint8 samples)
    - Builds distribution of normalized power magnitudes and compares against exponential(1)
      distribution using Kolmogorov-Smirnov test (empirical power ~ exponential for white noise)
    - Streaming: update()/finalize() supported; keeps bounded buffer and performs incremental FFTs
    - Parameters:
        mode: "bits" or "bytes" (default "bits")
        window_size: FFT window size in samples (default 2048)
        hop: hop size between windows (default window_size)
        downsample: keep every k-th sample to reduce work (default 1)
        max_windows: cap on number of windows processed (default 4096)
        alpha: significance level for pass/fail (default 0.01)
    """

    def __init__(self):
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._powers = []  # accumulate power values (flattened across windows)

    def describe(self) -> str:
        return "Advanced DFT spectral test (windowed power KS vs exponential)"

    def _samples_from_bytes(self, bts: bytes, mode: str) -> np.ndarray:
        if mode == "bits":
            try:
                import numpy as np
                bits = np.unpackbits(np.frombuffer(bts, dtype=np.uint8))
                # convert {0,1} to {-1,1} to be more like random +/- signal
                return bits.astype(np.float64) * 2.0 - 1.0
            except Exception:
                # fallback simple expansion
                arr = np.frombuffer(bts, dtype=np.uint8)
                return np.unpackbits(arr).astype(np.float64) * 2.0 - 1.0
        else:
            # treat bytes as uint8 samples centered at 0
            arr = np.frombuffer(bts, dtype=np.uint8).astype(np.float64)
            return arr - 127.5

    def _process_windows(self, samples: np.ndarray, window_size: int, hop: int, max_windows: int, downsample: int):
        if downsample > 1:
            samples = samples[::downsample]
        n = samples.size
        if n < window_size:
            return
        # number of windows
        nw = 1 + (n - window_size) // hop
        if max_windows is not None and nw > max_windows:
            nw = max_windows
        pow_list = []
        for i in range(nw):
            start = i * hop
            win = samples[start:start + window_size]
            if win.size < window_size:
                break
            # apply Hann window to reduce spectral leakage
            w = np.hanning(window_size)
            fft = np.fft.rfft(win * w)
            power = (np.abs(fft) ** 2) / float(window_size)
            # flatten excluding DC component to focus on spectral behavior
            if power.size > 1:
                pow_vals = power[1:].astype(np.float64)
            else:
                pow_vals = power.astype(np.float64)
            # normalize by mean power per-window to make exponential(1) target
            mean = pow_vals.mean() if pow_vals.size > 0 else 1.0
            if mean <= 0:
                mean = 1.0
            norm = pow_vals / mean
            pow_list.append(norm)
        if len(pow_list) > 0:
            # concatenate and extend global list
            self._powers.extend(np.concatenate(pow_list).tolist())

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        self._start = time.time()
        bts = data.to_bytes()
        mode = str(params.get("mode", "bits"))
        window_size = int(params.get("window_size", 2048))
        hop = int(params.get("hop", window_size))
        downsample = int(params.get("downsample", 1))
        max_windows = int(params.get("max_windows", 4096)) if params.get("max_windows") is not None else None
        alpha = float(params.get("alpha", 0.01))

        samples = self._samples_from_bytes(bts, mode)
        # process windows and collect normalized power values
        self._process_windows(samples, window_size, hop, max_windows, downsample)

        powers = np.array(self._powers, dtype=np.float64)
        p_value = None
        ks_stat = None
        mean_power = None
        if powers.size > 0:
            # The normalized power should follow exponential(1) for white noise
            ks_stat, p_value = stats.kstest(powers, 'expon')  # compares to exponential(0,1)
            mean_power = float(powers.mean())

        end = time.time()
        tr = TestResult(
            test_name=params.get("name", "dft_spectral_advanced"),
            passed=(p_value is None) or (p_value >= alpha),
            p_value=p_value,
            category="spectral",
            p_values={"ks": ks_stat if p_value is not None else None},
            metrics={"samples": int(samples.size), "power_samples": int(powers.size), "mean_power": mean_power},
            time_ms=(end - self._start) * 1000.0,
            bytes_processed=len(bts),
        )
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        if self._start is None:
            self._start = time.time()
        self._buf.extend(chunk)
        self._count_bytes += len(chunk)
        # keep buffer bounded
        max_buf = int(params.get("max_buffer_bytes", 1 << 20))
        if len(self._buf) > max_buf:
            # process chunk immediately and drop oldest half
            try:
                samples = self._samples_from_bytes(bytes(self._buf), params.get("mode", "bits"))
                self._process_windows(samples, int(params.get("window_size", 2048)), int(params.get("hop", params.get("window_size", 2048))), int(params.get("max_windows", 4096)), int(params.get("downsample", 1)))
            except Exception:
                pass
            half = len(self._buf) // 2
            self._buf = self._buf[half:]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bts = bytes(self._buf)
        # final processing
        try:
            samples = self._samples_from_bytes(bts, params.get("mode", "bits"))
            self._process_windows(samples, int(params.get("window_size", 2048)), int(params.get("hop", params.get("window_size", 2048))), int(params.get("max_windows", 4096)), int(params.get("downsample", 1)))
        except Exception:
            pass
        # delegate to run() to compute metrics from accumulated self._powers
        tr = self.run(BytesView(bts), params)
        # reset
        self._buf = bytearray()
        self._count_bytes = 0
        self._start = None
        self._powers = []
        return tr
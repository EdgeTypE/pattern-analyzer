from __future__ import annotations
"""
Autoencoder tabanlı anomalisi tespiti plugin.

- TestPlugin'den türetilir.
- BytesView kullanır.
- Hem batch (run) hem streaming (update/finalize) API'sini destekler.
- Varsayılan olarak hızlı stub modu kullanır (use_stub=True).
- Gerçek model için params['model_path'] ile keras modeli lazy-load eder.
"""

from typing import Dict, Any
import time
try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    from patternlab.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore


class AutoencoderAnomalyPlugin(TestPlugin):
    """
    Params:
      - model_path: optional path to saved keras autoencoder
      - window_size: int (default 1024)
      - downsample: int
      - reconstruction_threshold: float (anomaly threshold)
      - use_stub: bool (default True)
      - max_buffer_bytes: int for streaming buffer
    """

    requires = []

    def __init__(self):
        self._buffer = bytearray()
        self._model = None
        self._model_path = None

    def describe(self) -> str:
        return "Autoencoder-based reconstruction anomaly detection (batch + streaming)."

    def _load_model(self, model_path: str):
        if self._model is not None and self._model_path == model_path:
            return self._model
        try:
            import tensorflow as tf  # type: ignore
            model = tf.keras.models.load_model(model_path)
            self._model = model
            self._model_path = model_path
            return model
        except Exception as e:
            raise RuntimeError(f"failed_to_load_model:{e}")

    def _bytes_to_series(self, b: BytesView, window_size: int, downsample: int = 1):
        mv = b.data
        arr = mv.tobytes()
        if downsample <= 1:
            series = [float(x) / 255.0 for x in arr[:window_size]]
        else:
            series = []
            step = downsample
            for i in range(0, min(len(arr), window_size * step), step):
                block = arr[i:i+step]
                if not block:
                    break
                series.append(sum(block) / (len(block) * 255.0))
        if len(series) < window_size:
            series += [0.0] * (window_size - len(series))
        else:
            series = series[:window_size]
        return series

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        start = time.time()
        use_stub = params.get("use_stub", True)
        window_size = int(params.get("window_size", min(len(data), 1024)))
        downsample = int(params.get("downsample", 1))
        threshold = float(params.get("reconstruction_threshold", 0.02))
        inference_timeout_ms = int(params.get("inference_timeout_ms", 5000))

        series = self._bytes_to_series(data, window_size, downsample)

        if use_stub:
            # Simple reconstruction via moving-average filter as stub
            import statistics
            smoothed = []
            k = 5
            for i in range(len(series)):
                window = series[max(0, i-k+1):i+1]
                smoothed.append(sum(window)/len(window))
            mse = sum((a-b)**2 for a,b in zip(series, smoothed)) / (len(series) or 1)
            passed = mse < threshold
            tr = TestResult(
                test_name="autoencoder_anomaly",
                passed=bool(passed),
                p_value=max(0.0, min(1.0, 1.0 - mse)),
                category="ml_anomaly",
                metrics={"reconstruction_mse": mse, "method": "stub"},
                time_ms=(time.time()-start)*1000.0,
                bytes_processed=len(data),
            )
            return tr

        model_path = params.get("model_path")
        if not model_path:
            raise ValueError("model_path is required when use_stub=False")

        model = self._load_model(model_path)

        import numpy as np
        x = np.array(series, dtype=np.float32).reshape((1, len(series), 1))
        t0 = time.time()
        preds = model.predict(x, verbose=0)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000.0
        if elapsed_ms > inference_timeout_ms:
            raise RuntimeError("inference_timeout")

        # interpret as reconstruction
        recon = preds.reshape(-1)[:len(series)]
        mse = float(((recon - np.array(series))**2).mean())
        passed = mse < threshold
        tr = TestResult(
            test_name="autoencoder_anomaly",
            passed=bool(passed),
            p_value=max(0.0, min(1.0, 1.0 - mse)),
            category="ml_anomaly",
            metrics={"reconstruction_mse": mse, "method": "model"},
            time_ms=(time.time()-start)*1000.0,
            bytes_processed=len(data),
        )
        return tr

    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        max_buffer = int(params.get("max_buffer_bytes", 10 * 1024 * 1024))
        if not isinstance(chunk, (bytes, bytearray)):
            raise ValueError("chunk must be bytes")
        self._buffer.extend(chunk)
        if len(self._buffer) > max_buffer:
            extra = len(self._buffer) - max_buffer
            del self._buffer[:extra]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bv = BytesView(bytes(self._buffer))
        params = dict(params)
        params.setdefault("use_stub", True)
        tr = self.run(bv, params)
        tr.metrics.setdefault("streaming", True)
        return tr
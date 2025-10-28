from __future__ import annotations
"""
LSTM/GRU tabanlı zaman serisi anomali tespiti plugin.

- TestPlugin'den türetilir.
- BytesView kullanır.
- Hem batch (run) hem streaming (update/finalize) API'sini destekler.
- Varsayılan test modu hızlı unit-test çalıştırmaları için 'use_stub' = True kullanır.
- Gerçek model inference için params['model_path'] ile önceden eğitilmiş modeli lazy-load eder.
"""

from typing import Dict, Any, Optional
import time
import math
try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    # Relative import fallback for tests executed as top-level module
    from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore

class LSTMGRUAnomalyPlugin(TestPlugin):
    """
    Basit adapter plugin. Params:
      - window_size: int (bytes -> time-series length per sample)
      - downsample: int (downsample factor to reduce inference cost)
      - inference_timeout_ms: int (max inference time per run in ms)
      - model_path: str (optional path to saved TF model)
      - use_stub: bool (default True) -> hızlı heuristik, unit-test dostu
    """

    requires = []

    def __init__(self):
        self._buffer = bytearray()
        self._model = None
        self._model_path = None
        self._last_infer_ms = None

    def describe(self) -> str:
        return "LSTM/GRU-based time-series anomaly detection (supports streaming and batch)."

    # Lazy model loader (only loads tensorflow if model_path given and use_stub False)
    def _load_model(self, model_path: str):
        if self._model is not None and self._model_path == model_path:
            return self._model
        # Lazy import heavy dependency
        try:
            import tensorflow as tf  # type: ignore
            model = tf.keras.models.load_model(model_path)
            self._model = model
            self._model_path = model_path
            return model
        except Exception as e:
            raise RuntimeError(f"failed_to_load_model:{e}")

    # Convert BytesView/memoryview data to normalized float array for model; supports downsampling
    def _bytes_to_series(self, b: BytesView, window_size: int, downsample: int = 1):
        mv = b.data
        length = len(mv)
        # convert to list of ints then downsample
        arr = mv.tobytes()
        if downsample <= 1:
            series = [float(x) / 255.0 for x in arr[:window_size]]
        else:
            # Simple downsample: take mean of blocks
            series = []
            step = downsample
            for i in range(0, min(len(arr), window_size * step), step):
                block = arr[i:i+step]
                if not block:
                    break
                series.append(sum(block)/ (len(block)*255.0))
        # pad/truncate to window_size
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
        inference_timeout_ms = int(params.get("inference_timeout_ms", 5000))

        # If stub mode, run a fast statistical heuristic: compute normalized variance as anomaly score
        if use_stub:
            series = self._bytes_to_series(data, window_size, downsample)
            mean = sum(series)/len(series) if series else 0.0
            var = sum((x-mean)**2 for x in series)/(len(series) or 1)
            anomaly_score = float(var)
            passed = anomaly_score < 0.02  # arbitrary threshold for stub
            p_value = max(0.0, min(1.0, 1.0 - anomaly_score))  # not a real p-value, kept optional
            tr = TestResult(
                test_name="lstm_gru_anomaly",
                passed=bool(passed),
                p_value=float(p_value),
                category="ml_anomaly",
                metrics={"anomaly_score": anomaly_score, "method": "stub"},
                time_ms=(time.time()-start)*1000.0,
                bytes_processed=len(data),
            )
            return tr

        # Real model mode (lazy load)
        model_path = params.get("model_path")
        if not model_path:
            raise ValueError("model_path is required when use_stub=False")

        model = self._load_model(model_path)

        # Prepare input and run inference with timeout guard
        series = self._bytes_to_series(data, window_size, downsample)
        import numpy as np
        x = np.array(series, dtype=np.float32).reshape((1, len(series), 1))
        # simple timing guard (not interruptible) - record duration and fail if too slow
        t0 = time.time()
        preds = model.predict(x, verbose=0)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000.0
        if elapsed_ms > inference_timeout_ms:
            raise RuntimeError("inference_timeout")

        # Interpret preds depending on model output shape (reconstruction error or anomaly probability)
        if preds.shape[-1] == 1:
            # treat as probability
            anomaly_prob = float(preds[0, -1, 0]) if preds.ndim == 3 else float(preds[0,0])
            passed = anomaly_prob < 0.5
            metrics = {"anomaly_prob": anomaly_prob, "method": "model"}
            p_value = 1.0 - anomaly_prob
        else:
            # treat as reconstruction -> compute MSE between input and recon
            recon = preds.reshape(-1)[:len(series)]
            mse = float(((recon - np.array(series))**2).mean())
            passed = mse < 0.01
            metrics = {"reconstruction_mse": mse, "method": "model"}
            p_value = max(0.0, min(1.0, 1.0 - mse))

        tr = TestResult(
            test_name="lstm_gru_anomaly",
            passed=bool(passed),
            p_value=float(p_value),
            category="ml_anomaly",
            metrics=metrics,
            time_ms=(time.time()-start)*1000.0,
            bytes_processed=len(data),
        )
        return tr

    # Streaming API
    def update(self, chunk: bytes, params: Dict[str, Any]) -> None:
        # Accept bytes chunks and buffer them; keep buffer bounded to avoid memory issues
        max_buffer = int(params.get("max_buffer_bytes", 10 * 1024 * 1024))  # 10MB default
        if not isinstance(chunk, (bytes, bytearray)):
            raise ValueError("chunk must be bytes")
        self._buffer.extend(chunk)
        if len(self._buffer) > max_buffer:
            # drop oldest bytes (simple sliding window)
            extra = len(self._buffer) - max_buffer
            del self._buffer[:extra]

    def finalize(self, params: Dict[str, Any]) -> TestResult:
        bv = BytesView(bytes(self._buffer))
        # reuse run() semantics but mark method as streaming
        params = dict(params)
        params.setdefault("use_stub", True)  # streaming default to stub for speed unless overridden
        tr = self.run(bv, params)
        # annotate that this result came from streaming pipeline
        tr.metrics.setdefault("streaming", True)
        return tr
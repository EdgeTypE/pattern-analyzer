from __future__ import annotations
"""
Classifier labeler plugin.

- TestPlugin'den türetilir.
- BytesView kullanır.
- Streaming ve batch destekler.
- Lazy-load scikit-learn modeller (joblib) veya stub heuristics.
"""

from typing import Dict, Any, Optional, List
import time

try:
    from ..plugin_api import TestPlugin, TestResult, BytesView
except Exception:
    from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView  # type: ignore

class ClassifierLabelerPlugin(TestPlugin):
    """
    Params:
      - model_path: optional path to sklearn joblib file
      - labels: optional list of labels expected by the model (default common set)
      - use_stub: bool (default True) -> quick heuristic
      - inference_timeout_ms: int
      - max_buffer_bytes: int for streaming
    """

    requires = []

    def __init__(self):
        self._buffer = bytearray()
        self._model = None
        self._model_path = None

    def describe(self) -> str:
        return "Classifier-based labeler (ransomware/encrypted/etc.) using pre-trained sklearn models."

    def _load_model(self, model_path: str):
        if self._model is not None and self._model_path == model_path:
            return self._model
        try:
            import joblib  # type: ignore
            model = joblib.load(model_path)
            # Ensure model supports predict and predict_proba
            if not hasattr(model, "predict"):
                raise RuntimeError("model_missing_predict")
            self._model = model
            self._model_path = model_path
            return model
        except Exception as e:
            raise RuntimeError(f"failed_to_load_model:{e}")

    def _extract_features(self, b: BytesView, n_bins: int = 64):
        # Simple, fast histogram of byte values normalized; suitable for sklearn classifiers
        mv = b.data
        arr = mv.tobytes()
        bins = [0] * n_bins
        if arr:
            step = 256 // n_bins
            for v in arr:
                idx = min(n_bins - 1, v // step)
                bins[idx] += 1
            total = len(arr)
            features = [c / total for c in bins]
        else:
            features = [0.0] * n_bins
        return features

    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        start = time.time()
        use_stub = params.get("use_stub", True)
        model_path = params.get("model_path")
        labels: Optional[List[str]] = params.get("labels")
        inference_timeout_ms = int(params.get("inference_timeout_ms", 2000))

        features = self._extract_features(data, n_bins=int(params.get("n_bins", 64)))

        if use_stub:
            # Heuristic: high entropy -> likely encrypted; high repetition of small set -> maybe ransomware marker
            import math, statistics
            entropy = 0.0
            for p in features:
                if p > 0:
                    entropy -= p * math.log2(p)
            # simple thresholds (heuristic)
            is_encrypted = entropy > 7.0
            is_ransomware = features[0] > 0.2 and features[255 // max(1, (256//len(features)))] > 0.01 if len(features) > 1 else False
            detected = "encrypted" if is_encrypted else ("ransomware" if is_ransomware else "unknown")
            p_value = min(1.0, entropy / 8.0)
            tr = TestResult(
                test_name="classifier_labeler",
                passed= not (detected in ("encrypted","ransomware")),
                p_value=float(p_value),
                category="ml_label",
                metrics={"label": detected, "entropy": entropy, "method": "stub"},
                time_ms=(time.time()-start)*1000.0,
                bytes_processed=len(data),
            )
            return tr

        if not model_path:
            raise ValueError("model_path is required when use_stub=False")

        model = self._load_model(model_path)

        import numpy as np
        x = np.array(features, dtype=np.float32).reshape((1, -1))

        t0 = time.time()
        # predict_proba may not be available for all models; fallback to decision_function or predict
        probs = None
        label = None
        try:
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(x)[0].tolist()
                classes = getattr(model, "classes_", None)
                if classes is None:
                    classes = list(range(len(probs)))
                # choose top
                top_idx = int(np.argmax(probs))
                label = str(classes[top_idx])
            else:
                pred = model.predict(x)[0]
                label = str(pred)
                probs = None
        except Exception as e:
            raise RuntimeError(f"inference_failed:{e}")
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000.0
        if elapsed_ms > inference_timeout_ms:
            raise RuntimeError("inference_timeout")

        metrics = {"label": label, "method": "model"}
        if probs is not None:
            metrics["probabilities"] = probs
        tr = TestResult(
            test_name="classifier_labeler",
            passed=(label not in ("ransomware","encrypted")),
            p_value=(1.0 - max(probs)) if probs is not None else None,
            category="ml_label",
            metrics=metrics,
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
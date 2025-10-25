from __future__ import annotations
from typing import Dict, Any, List
import math
from patternlab.plugin_api import VisualPlugin, TestResult

class FFTPlaceholder(VisualPlugin):
    """
    Hafif bir FFT görselleştirme placeholder'ı.

    Yeni VisualPlugin API'sine uygun `render(self, result: TestResult, params: Dict[str, Any]) -> bytes`
    imzasını uygular ve basit bir SVG spektrum döndürür.
    """
    def describe(self) -> Dict[str, Any]:
        return {"name": "fft_placeholder", "version": "0.1"}

    def render(self, result: TestResult, params: Dict[str, Any]) -> bytes:
        # Metric'lerden sayısal değerleri al (varsa). Değer yoksa örnek veri üret.
        metrics = {}
        if isinstance(getattr(result, "metrics", None), dict):
            metrics = result.metrics

        values: List[float] = []
        # Sadece sayısal metrikleri al, sıralı şekilde
        for k in sorted(metrics.keys()):
            try:
                values.append(float(metrics[k]))
            except Exception:
                continue

        if not values:
            # Örnek spektrum: birkaç sinüs dalgasının toplamı -> pozitif magnitüdler
            values = [abs(math.sin(i * 0.3) * (1 + 0.5 * math.cos(i * 0.1))) for i in range(16)]

        # SVG oluştur
        width = int(params.get("width", 400))
        height = int(params.get("height", 120))
        padding = 4
        n = len(values)
        max_v = max(values) if values else 1.0
        bar_w = (width - 2 * padding) / max(1, n)

        parts: List[str] = []
        parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
        parts.append(f'<rect width="100%" height="100%" fill="#ffffff"/>')
        for i, v in enumerate(values):
            h = (v / max_v) * (height - 2 * padding)
            x = padding + i * bar_w
            y = height - padding - h
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w*0.9:.2f}" height="{h:.2f}" fill="#4a90e2"/>')
        parts.append('</svg>')

        svg = "\n".join(parts)
        return svg.encode("utf-8")
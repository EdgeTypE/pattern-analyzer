"""Plugin API definitions for PatternLab."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import math


@dataclass
class TestResult:
    """Test result container.

    Extended with observability fields:
      - time_ms: duration of the test execution in milliseconds (float or None)
      - bytes_processed: number of bytes the test observed/processed (int or None)
    The rest of the canonical schema remains the same.
    """
    __test__ = False
    test_name: str
    passed: bool
    p_value: Optional[float]
    category: str = "statistical"
    p_values: Dict[str, float] = field(default_factory=dict)
    effect_sizes: Dict[str, float] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    z_score: Optional[float] = None
    evidence: Optional[str] = None

    # Observability fields
    time_ms: Optional[float] = None
    bytes_processed: Optional[int] = None

    def __post_init__(self):
        # Allow None for p_value (no formal p-value), otherwise enforce [0.0, 1.0]
        if self.p_value is not None:
            if not (0.0 <= self.p_value <= 1.0):
                raise ValueError("p_value must be between 0 and 1 or None")
        # Normalize types for observability fields (if provided)
        if self.time_ms is not None:
            try:
                self.time_ms = float(self.time_ms)
            except Exception:
                raise ValueError("time_ms must be a number (milliseconds) or None")
        if self.bytes_processed is not None:
            try:
                self.bytes_processed = int(self.bytes_processed)
            except Exception:
                raise ValueError("bytes_processed must be an integer or None")

    @property
    def details(self) -> Dict[str, Any]:
        """Backwards-compatible read-only accessor for legacy 'details' name."""
        return self.metrics


def serialize_testresult(result: TestResult) -> Dict[str, Any]:
    """Serialize a TestResult into a JSON-compatible dict following the canonical schema.

    - Merges any legacy `details` dict into `metrics` if present to maintain backwards compatibility.
    - Exposes observability fields `time_ms` and `bytes_processed` in the serialized output.
    """
    # Collect metrics, merging legacy details if present
    metrics: Dict[str, Any] = {}
    legacy_details = getattr(result, 'details', None)
    if isinstance(legacy_details, dict):
        metrics.update(legacy_details)
    if isinstance(result.metrics, dict):
        metrics.update(result.metrics)

    out: Dict[str, Any] = {
        "test_name": result.test_name,
        "passed": result.passed,
        "p_value": result.p_value,
        "p_values": result.p_values or {},
        "effect_sizes": result.effect_sizes or {},
        "flags": result.flags or [],
        "metrics": metrics,
        "z_score": result.z_score,
        "evidence": result.evidence,
    }

    # Attach observability fields when present
    if getattr(result, "time_ms", None) is not None:
        out["time_ms"] = result.time_ms
    else:
        out["time_ms"] = None

    if getattr(result, "bytes_processed", None) is not None:
        out["bytes_processed"] = result.bytes_processed
    else:
        out["bytes_processed"] = None

    return out

class BytesView:
    """Memory-efficient byte view wrapper."""

    def __init__(self, data: Union[bytes, memoryview]):
        if isinstance(data, bytes):
            self._view = memoryview(data)
        else:
            self._view = data

    @property
    def data(self) -> memoryview:
        """Expose underlying memoryview for compatibility with plugins/tests."""
        return self._view

    def __len__(self) -> int:
        return len(self._view)

    def __getitem__(self, key):
        return self._view[key]

    def to_bytes(self) -> bytes:
        """Convert to bytes."""
        return bytes(self._view)

    def bit_view(self) -> list[int]:
        """Get real bit-level view. Returns list of bits (MSB-first per byte)."""
        try:
            import numpy as np
            # Use numpy for a fast bit unpacking from the underlying buffer
            return np.unpackbits(np.frombuffer(self._view, dtype=np.uint8)).tolist()
        except ImportError:
            # Fallback pure-Python implementation (MSB-first per byte)
            out: list[int] = []
            for v in self._view.cast('B'):
                for i in range(7, -1, -1):
                    out.append((v >> i) & 1)
            return out

    def text_view(self) -> Optional[str]:
        """Get text view (placeholder)."""
        try:
            return self._view.tobytes().decode("utf-8")
        except Exception:
            return None


class BasePlugin(ABC):
    """Base class for all plugins."""

    @abstractmethod
    def describe(self) -> str:
        """Return plugin description."""
        pass


class TransformPlugin(BasePlugin):
    """Base class for transformation plugins."""

    @abstractmethod
    def run(self, data: BytesView, params: Dict[str, Any]) -> BytesView:
        """Apply transformation."""
        pass


class TestPlugin(BasePlugin):
    """Base class for statistical test plugins."""
 
    # Use a plain list as the default for 'requires' to avoid exposing a dataclasses.Field object
    # when plugins inherit TestPlugin. This keeps runtime attribute access simple and iterable.
    requires: List[str] = []
 
    @abstractmethod
    def run(self, data: BytesView, params: Dict[str, Any]) -> TestResult:
        """Run statistical test."""
        pass

    def safe_run(self, data: BytesView, params: Dict[str, Any]):
        """Execute the test and convert unexpected exceptions into a structured error dict.

        Returns:
            TestResult when the test completes successfully, or
            dict with keys {"test_name": ..., "status": "error", "reason": "..."} when an exception occurs.

        Note: engine may inject the configured test name into the returned dict if needed.
        """
        try:
            return self.run(data, params)
        except Exception as e:
            return {"status": "error", "reason": str(e)}


class VisualPlugin(BasePlugin):
    """Base class for visualization plugins."""

    @abstractmethod
    def render(self, result: TestResult, params: Dict[str, Any]) -> bytes:
        """Generate visualization bytes (e.g., SVG/PNG)."""
        pass
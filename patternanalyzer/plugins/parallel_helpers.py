from typing import Dict, Any
import time

from patternanalyzer.plugin_api import TestPlugin, TestResult


class QuickStat(TestPlugin):
    """Lightweight deterministic statistical-like test used only for unit-tests.

    Computes a pseudo p-value deterministically from the input bytes so tests can
    compare outputs between sequential and parallel execution.
    """

    def describe(self) -> str:
        return "Quick deterministic statistical test"

    def run(self, data, params: Dict[str, Any]) -> TestResult:
        b = data.to_bytes()
        # deterministic pseudo-p-value in [0,1)
        s = sum(b)
        p = (s % 1000) / 1000.0
        return TestResult(test_name=params.get("name", "quickstat"), passed=(p > 0.05), p_value=p, category="statistical", p_values={"quickstat": p})


class BlockingTest(TestPlugin):
    """Test that deliberately sleeps for a configurable duration.

    Intended to exercise per-test timeout handling in parallel execution.
    """

    def describe(self) -> str:
        return "Blocking test for timeout simulation"

    def run(self, data, params: Dict[str, Any]) -> TestResult:
        sleep_seconds = float(params.get("sleep", 1.0))
        time.sleep(sleep_seconds)
        return TestResult(test_name=params.get("name", "blocking"), passed=True, p_value=1.0, category="statistical", p_values={"blocking": 1.0})
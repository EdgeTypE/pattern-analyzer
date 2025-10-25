import pytest
import json
from patternlab.engine import Engine
from patternlab.plugin_api import TransformPlugin, TestPlugin, VisualPlugin, TestResult


class BadTransform(TransformPlugin):
    def describe(self):
        return "Bad transform that raises"

    def run(self, data, params):
        raise RuntimeError("boom transform")


class GoodTest(TestPlugin):
    def describe(self):
        return "Good test"

    def run(self, data, params):
        # Return a minimal successful TestResult
        return TestResult(test_name="goodtest", passed=True, p_value=None)


class BadVisual(VisualPlugin):
    def describe(self):
        return "Bad visual that raises"

    def render(self, result, params):
        raise ValueError("visual failed")


def test_transform_error_reports_status_error():
    engine = Engine()
    engine.register_transform("bad", BadTransform())

    out = engine.analyze(b"\x00\x01\x02", {"transforms": [{"name": "bad", "params": {}}]})

    assert isinstance(out, dict)
    assert "results" in out
    assert isinstance(out["results"], list)
    assert out["results"], "Expected at least one result entry"
    r = out["results"][0]
    assert r.get("status") == "error"
    assert "details" in r
    assert "boom transform" in r["details"]


def test_visual_error_reported_in_visual_errors_and_does_not_fail_test():
    engine = Engine()
    engine.register_test("goodtest", GoodTest())
    engine.register_visual("badvisual", BadVisual())

    out = engine.analyze(
        b"\x00\x01\x02",
        {
            "tests": [{"name": "goodtest", "params": {}}],
        },
    )

    assert out["results"], "Expected at least one result"
    r = out["results"][0]

    # Engine should keep the test completed while reporting visual errors separately.
    assert r.get("status") == "completed"
    # The serialized result must include the visual_errors entry for the failing visual plugin.
    assert "visual_errors" in r and any(v.get("visual_name") == "badvisual" for v in r.get("visual_errors"))
    # GoodTest returns passed=True with p_value=None in the TestResult above.
    assert r.get("passed") is True



# --- New observability tests ---

def test_time_and_bytes_measured():
    engine = Engine()

    class ObsTest(TestPlugin):
        def describe(self):
            return "Observability test"

        def run(self, data, params):
            # touch the bytes to simulate processing
            _ = data.to_bytes()
            return TestResult(test_name="obs_test", passed=True, p_value=None)

    engine.register_test("obs_test", ObsTest())

    data = b"\x00\x01\x02\x03\x04"
    out = engine.analyze(data, {"tests": [{"name": "obs_test", "params": {}}]})

    assert out["results"], "Expected at least one result"
    r = out["results"][0]

    # Engine should have exposed observability fields
    assert "time_ms" in r
    assert r["time_ms"] is not None
    assert isinstance(r["time_ms"], (int, float))
    assert r["time_ms"] >= 0

    assert "bytes_processed" in r
    assert r["bytes_processed"] == len(data)


def test_logger_writes_jsonl(tmp_path):
    engine = Engine()

    class ObsTest2(TestPlugin):
        def describe(self):
            return "Observability test 2"

        def run(self, data, params):
            _ = data.to_bytes()
            return TestResult(test_name="obs_test2", passed=True, p_value=None)

    engine.register_test("obs_test2", ObsTest2())

    data = b"\x00\x01\x02"
    log_file = tmp_path / "pl.jsonl"

    out = engine.analyze(
        data,
        {
            "tests": [{"name": "obs_test2", "params": {}}],
            "log_path": str(log_file),
        },
    )

    # Read last line of the JSONL log
    text = log_file.read_text(encoding="utf-8").strip()
    lines = [l for l in text.splitlines() if l.strip()]
    assert lines, "Expected at least one log line"
    entry = json.loads(lines[-1])
 
    assert entry.get("test_name") == "obs_test2"
    assert "time_ms" in entry
    assert entry.get("bytes_processed") == len(data)
 
 
def test_report_meta_json_and_html(tmp_path):
    engine = Engine()
    # reuse GoodTest defined above
    engine.register_test("goodtest", GoodTest())
 
    data = b"\x00\x01\x02"
    html_file = tmp_path / "pl_report.html"
    out = engine.analyze(
        data,
        {
            "tests": [{"name": "goodtest", "params": {}}],
            "html_report": str(html_file),
        },
    )
 
    # JSON output must contain meta with expected keys
    assert "meta" in out
    meta = out["meta"]
    assert isinstance(meta, dict)
    for key in ("python", "platform", "config_hash", "input_hash", "plugins"):
        assert key in meta
    assert meta.get("config_hash") is not None
    assert meta.get("input_hash") is not None
 
    # HTML must be written and include a Meta section and the config_hash value
    html_text = html_file.read_text(encoding="utf-8")
    assert "<h2>Meta</h2>" in html_text
    # config_hash should appear in the HTML (rendered via json.dumps)
    assert str(meta.get("config_hash")) in html_text
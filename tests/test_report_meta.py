import json
from patternanalyzer.engine import Engine
from patternanalyzer.plugin_api import TestPlugin, TestResult

def test_report_meta_contains_extended_fields(tmp_path):
    engine = Engine()

    class GoodTest(TestPlugin):
        def describe(self):
            return "Good test for meta"
        def run(self, data, params):
            return TestResult(test_name="goodtest", passed=True, p_value=None)

    engine.register_test("goodtest", GoodTest())

    html_file = tmp_path / "pl_report_meta.html"
    config = {
        "tests": [{"name": "goodtest", "params": {"seed": 999}}],
        "html_report": str(html_file),
        "profile": "fast",
        "seed": 12345,
    }

    out = engine.analyze(b"\x00\x01\x02", config)

    assert "meta" in out and isinstance(out["meta"], dict)
    meta = out["meta"]

    # New meta fields must exist (engine_version may be None when not installed as a distribution)
    assert "engine_version" in meta
    assert "plugin_versions" in meta and isinstance(meta["plugin_versions"], dict)
    assert "cpu" in meta and isinstance(meta["cpu"], dict)
    assert "profile" in meta
    assert "test_seed" in meta and isinstance(meta["test_seed"], dict)

    # Profile must reflect provided override
    assert meta["profile"] == "fast"

    # Seeds must reflect config
    assert meta["test_seed"].get("global") == 12345
    assert meta["test_seed"].get("per_test", {}).get("goodtest") == 999

    # plugin_versions should include the registered test (value may be None)
    assert "goodtest" in meta["plugin_versions"]

    # HTML should have been emitted and include a Meta section
    html_text = html_file.read_text(encoding="utf-8")
    assert "<h2>Meta</h2>" in html_text
    # config_hash should appear in HTML (rendered via json.dumps)
    assert str(meta.get("config_hash")) in html_text
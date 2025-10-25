import json
from patternlab.engine import Engine
from patternlab.plugin_api import TestPlugin, TestResult

def test_html_report_contains_collapsible_and_summarized_metrics(tmp_path):
    engine = Engine()

    class LargeMetricsTest(TestPlugin):
        def describe(self):
            return "Produces a large metrics list"

        def run(self, data, params):
            # metrics contains a long list that should be summarized in the report
            big_list = list(range(60))
            return TestResult(
                test_name="large_metrics",
                passed=True,
                p_value=0.02,
                p_values={"large_metrics": 0.02},
                metrics={"samples": big_list},
            )

    engine.register_test("large_metrics", LargeMetricsTest())

    html_file = tmp_path / "pl_large_report.html"
    out = engine.analyze(
        b"\x00" * 10,
        {
            "tests": [{"name": "large_metrics", "params": {}}],
            "html_report": str(html_file),
        },
    )

    # Basic JSON meta presence
    assert "meta" in out and isinstance(out["meta"], dict)

    # HTML file created
    html_text = html_file.read_text(encoding="utf-8")

    # Must contain Meta and a collapsible details section for metrics
    assert "<h2>Meta</h2>" in html_text
    assert "<details" in html_text or "Metrics" in html_text

    # New: ensure help icon data-test attribute is rendered for the plugin description
    assert 'data-test="plugin-desc-large_metrics"' in html_text

    # New: descriptions JSON blob should be present (rendered by the engine into the template)
    assert '<script id="pluginDescriptions"' in html_text
    # and the JSON should mention the test key
    assert '"large_metrics"' in html_text or "'large_metrics'" in html_text

    # Summarization: the long list should be represented with its length in the emitted JSON
    # Look for '"length": 60' which is produced by the summarizer for long lists
    assert '"length": 60' in html_text or "'length': 60" in html_text
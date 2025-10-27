from patternlab.plugins.classifier_labeler import ClassifierLabelerPlugin
from patternlab.plugin_api import BytesView

def test_classifier_labeler_stub_batch():
    data = bytes([i % 256 for i in range(1024)])
    bv = BytesView(data)
    plugin = ClassifierLabelerPlugin()
    res = plugin.run(bv, {"use_stub": True, "n_bins": 64})
    assert res.test_name == "classifier_labeler"
    assert hasattr(res, "passed")
    assert isinstance(res.metrics, dict)
    assert "label" in res.metrics

def test_classifier_labeler_streaming_stub():
    plugin = ClassifierLabelerPlugin()
    for i in range(8):
        plugin.update(bytes([(i * 31) % 256] * 128), {})
    res = plugin.finalize({"use_stub": True, "n_bins": 64})
    assert res.test_name == "classifier_labeler"
    assert res.metrics.get("streaming", True) is True
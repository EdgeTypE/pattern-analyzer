from patternlab.plugins.autoencoder_anomaly import AutoencoderAnomalyPlugin
from patternlab.plugin_api import BytesView

def test_autoencoder_stub_batch():
    data = bytes([((i*7) % 256) for i in range(1024)])
    bv = BytesView(data)
    plugin = AutoencoderAnomalyPlugin()
    res = plugin.run(bv, {"use_stub": True, "window_size": 256, "downsample": 1})
    assert res.test_name == "autoencoder_anomaly"
    assert hasattr(res, "passed")
    assert isinstance(res.p_value, float) or res.p_value is None
    assert isinstance(res.metrics, dict)

def test_autoencoder_streaming_stub():
    plugin = AutoencoderAnomalyPlugin()
    for i in range(8):
        plugin.update(bytes([(i*3) % 256] * 128), {})
    res = plugin.finalize({"use_stub": True, "window_size": 256})
    assert res.test_name == "autoencoder_anomaly"
    assert res.metrics.get("streaming", True) is True
from patternanalyzer.plugins.lstm_gru_anomaly import LSTMGRUAnomalyPlugin
from patternanalyzer.plugin_api import BytesView

def test_lstm_stub_batch():
    data = bytes([i % 256 for i in range(1024)])
    bv = BytesView(data)
    plugin = LSTMGRUAnomalyPlugin()
    res = plugin.run(bv, {"use_stub": True, "window_size": 256, "downsample": 1})
    assert res.test_name == "lstm_gru_anomaly"
    assert hasattr(res, "passed")
    assert isinstance(res.p_value, float) or res.p_value is None
    assert isinstance(res.metrics, dict)

def test_lstm_streaming_stub():
    plugin = LSTMGRUAnomalyPlugin()
    # stream 4 chunks
    for i in range(4):
        plugin.update(bytes([i % 256] * 256), {})
    res = plugin.finalize({"use_stub": True, "window_size": 256})
    assert res.test_name == "lstm_gru_anomaly"
    assert res.metrics.get("streaming", True) is True
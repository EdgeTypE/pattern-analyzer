import math
import random
from patternlab.plugins.conditional_entropy import ConditionalEntropyTest
from patternlab.plugin_api import BytesView

def _chunks(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i+size]

def test_conditional_entropy_batch_vs_stream():
    rnd = random.Random(42)
    size_bytes = 2048
    data = bytes(rnd.getrandbits(8) for _ in range(size_bytes))

    params = {"mode": "bytes", "downsample": 1, "max_buffer_bytes": 1 << 16}

    # batch
    p_batch = ConditionalEntropyTest()
    tr_batch = p_batch.run(BytesView(data), params)
    assert "conditional_entropy" in tr_batch.metrics

    # streaming
    p_stream = ConditionalEntropyTest()
    for ch in _chunks(data, 512):
        p_stream.update(ch, params)
    tr_stream = p_stream.finalize(params)
    assert "conditional_entropy" in tr_stream.metrics

    be = tr_batch.metrics.get("conditional_entropy")
    se = tr_stream.metrics.get("conditional_entropy")
    assert be is not None and se is not None
    assert math.isfinite(be) and math.isfinite(se)
    assert math.isclose(be, se, rel_tol=1e-9, abs_tol=1e-9)
    assert tr_stream.bytes_processed == len(data)
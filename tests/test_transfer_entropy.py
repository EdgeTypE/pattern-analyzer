import math
import random
from patternlab.plugins.transfer_entropy import TransferEntropyTest
from patternlab.plugin_api import BytesView

def _chunks(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i+size]

def test_transfer_entropy_batch_vs_stream():
    rnd = random.Random(777)
    size_bytes = 2048
    data = bytes(rnd.getrandbits(8) for _ in range(size_bytes))

    params = {"mode": "bytes", "downsample": 1, "max_buffer_bytes": 1 << 16}

    # batch
    p_batch = TransferEntropyTest()
    tr_batch = p_batch.run(BytesView(data), params)
    assert "transfer_entropy" in tr_batch.metrics

    # streaming
    p_stream = TransferEntropyTest()
    for ch in _chunks(data, 512):
        p_stream.update(ch, params)
    tr_stream = p_stream.finalize(params)
    assert "transfer_entropy" in tr_stream.metrics

    bm = tr_batch.metrics.get("transfer_entropy")
    sm = tr_stream.metrics.get("transfer_entropy")
    assert bm is not None and sm is not None
    assert math.isfinite(bm) and math.isfinite(sm)
    assert math.isclose(bm, sm, rel_tol=1e-9, abs_tol=1e-9)
    assert tr_stream.bytes_processed == len(data)
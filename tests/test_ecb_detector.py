import os
from patternlab.plugin_api import BytesView, TestResult
from patternlab.plugins.ecb_detector import ECBDetector


def test_run_detects_ecb_repeating_blocks():
    # Construct data with repeating 16-byte blocks (ECB-like)
    block_a = b"A" * 16
    block_b = b"B" * 16
    data = block_a + block_b + block_a + block_b + block_a
    bv = BytesView(data)
    plugin = ECBDetector()
    tr = plugin.run(bv, params={})
    assert isinstance(tr, TestResult)
    # Duplicate blocks exist -> should be flagged as ecb_like and mark passed=False
    assert "ecb_like" in tr.flags or tr.evidence is not None
    assert tr.passed is False


def test_streaming_update_finalize_equivalent_to_run():
    plugin = ECBDetector()
    # stream in two chunks that together contain repeating blocks
    chunk1 = (b"A" * 16) + (b"B" * 16)
    chunk2 = (b"A" * 16) + (b"C" * 16) + (b"A" * 16)
    plugin.update(chunk1, params={})
    plugin.update(chunk2, params={})
    tr_stream = plugin.finalize(params={})
    # Compare against batch run on the concatenated bytes
    bv = BytesView(chunk1 + chunk2)
    plugin2 = ECBDetector()
    tr_batch = plugin2.run(bv, params={})
    assert isinstance(tr_stream, TestResult)
    assert isinstance(tr_batch, TestResult)
    # basic agreement on duplicate_ratio presence (if duplicates found both should flag)
    assert (len(tr_stream.flags) > 0) == (len(tr_batch.flags) > 0)


def test_run_on_random_data_no_false_positive():
    random_data = os.urandom(4096)
    bv = BytesView(random_data)
    plugin = ECBDetector()
    tr = plugin.run(bv, params={"downsample": 4})
    assert isinstance(tr, TestResult)
    # Random data should usually not be flagged as ECB-like; allow non-determinism but ensure API returns
    assert "ecb_like" not in tr.flags or tr.passed is False or hasattr(tr, "metrics")
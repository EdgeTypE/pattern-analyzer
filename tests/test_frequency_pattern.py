import os
from patternanalyzer.plugin_api import BytesView, TestResult
from patternanalyzer.plugins.frequency_pattern import FrequencyPattern


def test_run_detects_vigenere_like_ioc():
    # Construct data where each modulo-3 position is dominated by a single byte value
    # This produces high IoC per bin and should be detected as vigenere_like
    parts = []
    N = 1024
    for i in range(N):
        if (i % 3) == 0:
            parts.append(b"E")  # repeated byte
        elif (i % 3) == 1:
            parts.append(b"T")
        else:
            parts.append(b"A")
    data = b"".join(parts)
    bv = BytesView(data)
    plugin = FrequencyPattern()
    tr = plugin.run(bv, params={"max_key_len": 8, "vigenere_ioc_threshold": 0.02})
    assert isinstance(tr, TestResult)
    assert "vigenere_like" in tr.flags or tr.evidence is not None
    assert tr.passed is False


def test_streaming_equivalent_to_run():
    plugin = FrequencyPattern()
    # stream in two chunks
    chunk1 = (b"E" * 512) + (b"T" * 512)
    chunk2 = (b"A" * 512) + (b"E" * 256)
    plugin.update(chunk1, params={})
    plugin.update(chunk2, params={})
    tr_stream = plugin.finalize(params={"max_key_len": 6})
    bv = BytesView(chunk1 + chunk2)
    plugin2 = FrequencyPattern()
    tr_batch = plugin2.run(bv, params={"max_key_len": 6})
    assert isinstance(tr_stream, TestResult)
    assert isinstance(tr_batch, TestResult)
    # Presence of vigenere_like flag should be consistent
    assert (len(tr_stream.flags) > 0) == (len(tr_batch.flags) > 0)
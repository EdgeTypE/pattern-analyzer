from patternanalyzer.plugin_api import BytesView, TestResult
from patternanalyzer.plugins.known_constants_search import KnownConstantsSearch, AES_SBOX


def test_detects_aes_sbox_in_header():
    # Put AES S-box at the start followed by random bytes
    data = AES_SBOX + b"\x00" * 1024
    bv = BytesView(data)
    plugin = KnownConstantsSearch()
    tr = plugin.run(bv, params={"header_limit": 512})
    assert isinstance(tr, TestResult)
    assert tr.passed is False
    assert any(m["table"] == "aes_sbox" for m in tr.metrics.get("matches", []))


def test_streaming_update_finalize_reports_match():
    plugin = KnownConstantsSearch()
    # stream the sbox across two chunks (split in the middle)
    split = len(AES_SBOX) // 2
    chunk1 = AES_SBOX[:split] + b"\x11" * 100
    chunk2 = AES_SBOX[split:] + b"\x22" * 100
    plugin.update(chunk1, params={})
    plugin.update(chunk2, params={})
    tr = plugin.finalize(params={})
    assert isinstance(tr, TestResult)
    assert tr.passed is False
    assert tr.metrics["num_matches"] >= 1
import math
import random
from patternanalyzer.engine import Engine

def _find_result(results, name):
    for r in results:
        if r.get("test_name") == name:
            return r
    return None

def _chunks(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i+size]

def test_streaming_matches_batch_for_large_input():
    # Deterministic randomness for test reproducibility
    rnd = random.Random(12345)
    # moderately large dataset (keeps test fast while exercising streaming logic)
    size_bytes = 4096  # 4 KiB -> 32768 bits
    data = bytes(rnd.getrandbits(8) for _ in range(size_bytes))

    eng = Engine()

    config = {
        "tests": [
            {"name": "monobit", "params": {}},
            {"name": "runs", "params": {"min_bits": 20}},
            {"name": "block_frequency", "params": {"block_size": 8}},
            {"name": "cusum", "params": {"min_bits": 100}},
            {"name": "serial", "params": {"max_m": 4}},
        ],
        "fdr_q": 0.05
    }

    # Batch (regular) analysis
    batch_out = eng.analyze(data, config)
    assert "results" in batch_out and "scorecard" in batch_out

    # Streaming analysis: split into smaller chunks
    chunk_size = 512
    stream_iter = _chunks(data, chunk_size)
    stream_out = eng.analyze_stream(stream_iter, config)
    assert "results" in stream_out and "scorecard" in stream_out

    # For each target test, ensure presence and p_value parity (within tolerance)
    tol = 1e-6
    for test_name in ("monobit", "runs", "block_frequency", "cusum", "serial"):
        bres = _find_result(batch_out["results"], test_name)
        sres = _find_result(stream_out["results"], test_name)
        assert bres is not None, f"{test_name} missing in batch results"
        assert sres is not None, f"{test_name} missing in stream results"

        # p_value may be None for non-statistical plugins; ensure numeric and close
        bp = bres.get("p_value")
        sp = sres.get("p_value")
        assert bp is not None and sp is not None, f"{test_name} returned no p_value"
        assert math.isfinite(bp) and math.isfinite(sp)
        assert math.isclose(bp, sp, rel_tol=1e-6, abs_tol=tol), f"{test_name} p_value mismatch: batch={bp} stream={sp}"

        # Compare some metric fields that should be identical (total_bits / block_count etc.)
        bmetrics = bres.get("metrics", {})
        smetrics = sres.get("metrics", {})
        if "total_bits" in bmetrics:
            assert bmetrics["total_bits"] == smetrics.get("total_bits")
        if test_name == "block_frequency":
            assert bmetrics.get("block_size") == smetrics.get("block_size")
            assert bmetrics.get("block_count") == smetrics.get("block_count")
            # ones_counts arrays length should match
            assert len(bmetrics.get("ones_counts", [])) == len(smetrics.get("ones_counts", []))
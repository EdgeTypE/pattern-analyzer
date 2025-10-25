import os
import sys
import json
import subprocess

def test_bench_calibrate_creates_artifacts(tmp_path):
    outdir = tmp_path / "bench_out"
    cmd = [sys.executable, "-m", "patternlab.cli", "bench", "--calibrate", "--samples", "50", "--seed", "1", "--out-dir", str(outdir), "--profile", "nist"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr, file=sys.stderr)
    assert res.returncode == 0
    summary = outdir / "bench_summary.json"
    assert summary.exists()
    with open(summary, "r", encoding="utf-8") as f:
        s = json.load(f)
    assert "tests" in s
    # ensure at least one test entry has ks_artifact or qq plot
    found_artifact = False
    for tname, tinfo in s.get("tests", {}).items():
        if isinstance(tinfo, dict) and ("ks_artifact" in tinfo or "qq_plot" in tinfo):
            found_artifact = True
            break
    assert found_artifact
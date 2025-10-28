import os
from patternanalyzer.validation import p_value_calibration as pvc


def test_calibrate_defaults_and_csv(tmp_path):
    out = pvc.calibrate_p_values(
        num_streams=50,
        stream_length=128,
        generator_mode="python",
        generator_seed=123,
        test_func=None,
        save_csv=str(tmp_path / "cal.csv"),
    )
    assert "p_values" in out
    pvals = out["p_values"]
    assert len(pvals) == 50
    assert all(0.0 <= p <= 1.0 for p in pvals)
    assert "qq_theoretical" in out and "qq_empirical" in out
    assert len(out["qq_theoretical"]) == len(out["qq_empirical"]) == len(pvals)
    ks = out["ks"]
    assert 0.0 <= ks["D"] <= 1.0
    assert 0.0 <= ks["p_value"] <= 1.0
    # CSV should exist and contain header
    csv_path = tmp_path / "cal.csv"
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "stream_index" in text and "p_value" in text


def test_deterministic_with_seed():
    a = pvc.calibrate_p_values(num_streams=20, stream_length=64, generator_mode="python", generator_seed=999, test_func=None)
    b = pvc.calibrate_p_values(num_streams=20, stream_length=64, generator_mode="python", generator_seed=999, test_func=None)
    assert a["p_values"] == b["p_values"]
    # Different seed should (very likely) produce different p-values
    c = pvc.calibrate_p_values(num_streams=20, stream_length=64, generator_mode="python", generator_seed=1000, test_func=None)
    assert a["p_values"] != c["p_values"]
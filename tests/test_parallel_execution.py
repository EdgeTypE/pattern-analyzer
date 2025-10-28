import time
import math
from patternanalyzer.engine import Engine
from patternanalyzer.plugins.parallel_helpers import QuickStat, BlockingTest

def _find_result(results, name):
    for r in results:
        if r.get("test_name") == name:
            return r
    return None

def test_parallel_matches_sequential():
    eng = Engine()
    eng.register_test("quickstat", QuickStat())
    data = bytes([1,2,3,4,5,6,7,8,9,10])
    config_seq = {
        "tests": [{"name":"quickstat", "params": {"name":"quickstat"}}],
        "fdr_q": 0.05,
        "parallel": False
    }
    config_par = dict(config_seq)
    config_par["parallel"] = True
    config_par["max_workers"] = 2
    config_par["per_test_timeout"] = 5.0

    seq_out = eng.analyze(data, config_seq)
    par_out = eng.analyze(data, config_par)

    assert "results" in seq_out and "results" in par_out
    s = _find_result(seq_out["results"], "quickstat")
    p = _find_result(par_out["results"], "quickstat")
    assert s is not None and p is not None
    assert math.isclose(s.get("p_value"), p.get("p_value"), rel_tol=1e-9, abs_tol=1e-12)

def test_parallel_timeout_enforced():
    eng = Engine()
    eng.register_test("blocking", BlockingTest())
    data = bytes([0]*10)
    config = {
        "tests": [{"name":"blocking", "params": {"sleep": 2.0, "name":"blocking"}}],
        "parallel": True,
        "per_test_timeout": 0.5,
        "max_workers": 2
    }
    out = eng.analyze(data, config)
    res = _find_result(out["results"], "blocking")
    assert res is not None
    assert res.get("status") == "error"
    assert "timeout" in (res.get("reason") or "")
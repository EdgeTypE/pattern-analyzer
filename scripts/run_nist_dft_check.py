import json
import random
from patternanalyzer.plugin_api import BytesView
from patternanalyzer.plugins.nist_dft_spectral import NISTDFTSpectralTest

def run_checks():
    plugin = NISTDFTSpectralTest()
    results = {}

    # Strong periodic pattern -> expect small p-value and failure
    data = bytes([0b10101010] * 128)  # 128 bytes -> 1024 bits
    bv = BytesView(data)
    res = plugin.run(bv, params={})
    results["periodic"] = {
        "test_name": res.test_name,
        "p_value": res.p_value,
        "passed": res.passed,
        "metrics": res.metrics,
    }

    # Deterministic pseudorandom -> expect larger p-value and pass
    rng = random.Random(0)
    data = bytes(rng.getrandbits(8) for _ in range(256))
    bv = BytesView(data)
    res = plugin.run(bv, params={})
    results["random"] = {
        "test_name": res.test_name,
        "p_value": res.p_value,
        "passed": res.passed,
        "metrics": res.metrics,
    }

    # Small data -> skipped, no p-value
    data = bytes([0x00] * 5)
    bv = BytesView(data)
    res = plugin.run(bv, params={})
    results["small"] = {
        "test_name": res.test_name,
        "p_value": res.p_value,
        "passed": res.passed,
        "flags": getattr(res, "flags", None),
        "metrics": res.metrics,
    }

    print(json.dumps(results, default=str, indent=2))

if __name__ == "__main__":
    run_checks()
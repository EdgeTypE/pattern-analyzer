import pytest
from patternanalyzer.plugin_api import BytesView
from patternanalyzer.plugins.dotplot import DotplotTest

def test_dotplot_detects_repeats():
    # Create data with a long repeated region (A...) followed by different bytes (B...)
    data = b"A" * 800 + b"B" * 200
    bv = BytesView(data)
    plugin = DotplotTest()
    params = {"window_size": 40, "step": 40, "preview_len": len(data), "hash_only": True}
    result = plugin.run(bv, params=params)

    assert result.test_name == "dotplot"
    metrics = result.metrics
    matrix = metrics["matrix"]
    n = metrics["n_windows"]
    assert n > 0

    # Count identical-window matches (1.0). Off-diagonal ones indicate repeated windows.
    offdiag = 0
    for i in range(n):
        for j in range(n):
            if i != j and matrix[i][j] == 1.0:
                offdiag += 1

    # Expect many off-diagonal matches from the repeated A region: 800/40 = 20 windows -> 20*19 = 380
    assert offdiag >= 300
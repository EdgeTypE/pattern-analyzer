import pytest
from patternlab.plugins.fft_placeholder import FFTPlaceholder
from patternlab.plugin_api import TestResult

def test_fft_placeholder_renders_svg_from_metrics():
    result = TestResult(test_name="fft", passed=True, p_value=0.5, metrics={"f1": 1.0, "f2": 2.0})
    plugin = FFTPlaceholder()
    out = plugin.render(result, params={"width":200, "height":100})
    assert isinstance(out, bytes)
    text = out.decode("utf-8")
    assert text.lstrip().startswith("<svg")
    assert 'width="200"' in text
    assert "<rect" in text

def test_fft_placeholder_renders_svg_defaults_when_no_metrics():
    result = TestResult(test_name="fft2", passed=False, p_value=0.1)
    plugin = FFTPlaceholder()
    out = plugin.render(result, params={})
    assert isinstance(out, bytes)
    text = out.decode("utf-8")
    assert text.lstrip().startswith("<svg")
    assert 'width="' in text and 'height="' in text
import importlib.metadata as im
import pytest
from patternlab.engine import Engine
from patternlab.plugins.vigenere import VigenerePlugin
from patternlab.plugins.xor_const import XOPlugin
from patternlab.plugins.monobit import MonobitTest
from patternlab.plugins.cusum import CumulativeSumsTest
from patternlab.plugins.binary_matrix_rank import BinaryMatrixRankTest
from patternlab.plugins.longest_run import LongestRunOnesTest

class FakeEP:
    def __init__(self, name, cls):
        self.name = name
        self._cls = cls

    def load(self):
        return self._cls

def fake_entry_points(group=None):
    if group == 'patternlab.plugins':
        return [
            FakeEP('vigenere', VigenerePlugin),
            FakeEP('xor_const', XOPlugin),
            FakeEP('monobit', MonobitTest),
            FakeEP('cusum', CumulativeSumsTest),
            FakeEP('binary_matrix_rank', BinaryMatrixRankTest),
            FakeEP('longest_run', LongestRunOnesTest),
        ]
    return []

def test_entrypoint_discovery(monkeypatch):
    # Monkeypatch importlib.metadata.entry_points used by Engine to return our fake EPs
    monkeypatch.setattr(im, 'entry_points', fake_entry_points)
    e = Engine()
    transforms = e.get_available_transforms()
    tests = e.get_available_tests()
    # vigenere should be available via entry point discovery
    assert 'vigenere' in transforms
    # newly added plugins should be discoverable as tests
    assert 'cusum' in tests
    assert 'binary_matrix_rank' in tests
    assert 'longest_run' in tests

def test_entrypoint_discovery_e2e():
    # End-to-end test using the real installed entry points (requires editable install)
    eps = im.entry_points(group='patternlab.plugins')
    if not eps:
        pytest.skip("No entry points installed in environment")
    e = Engine()
    transforms = e.get_available_transforms()
    tests = e.get_available_tests()
    # Basic assertions that bundled and entry-point plugins are discovered
    assert 'vigenere' in transforms
    assert 'xor_const' in transforms
    assert 'monobit' in tests
    # verify new plugins are present when installed
    assert 'cusum' in tests
    assert 'binary_matrix_rank' in tests
    assert 'longest_run' in tests
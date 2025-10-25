import importlib.metadata as im
import pytest


def get_entry_points(group):
    try:
        # Modern API may accept group=...
        return im.entry_points(group=group)
    except TypeError:
        # Older/newer variants return a mapping or EntryPoints object
        all_eps = im.entry_points()
        if hasattr(all_eps, "select"):
            return all_eps.select(group=group)
        if isinstance(all_eps, dict):
            return all_eps.get(group, [])
        return []


def test_entry_points_e2e():
    eps = get_entry_points("patternlab.plugins")
    if not eps:
        pytest.skip("No entry points installed in environment")
    names = {getattr(ep, "name", None) for ep in eps}
    expected = {
        "vigenere",
        "xor_const",
        "monobit",
        "cusum",
        "binary_matrix_rank",
        "longest_run",
    }
    assert expected & names


def test_entry_points_monkeypatched(monkeypatch):
    class FakeEP:
        def __init__(self, name):
            self.name = name

    def fake_entry_points(group=None):
        if group == "patternlab.plugins":
            return [FakeEP("vigenere"), FakeEP("xor_const"), FakeEP("monobit")]
        return []

    monkeypatch.setattr(im, "entry_points", fake_entry_points)
    eps = get_entry_points("patternlab.plugins")
    names = {ep.name for ep in eps}
    assert "vigenere" in names
    assert "xor_const" in names
    assert "monobit" in names
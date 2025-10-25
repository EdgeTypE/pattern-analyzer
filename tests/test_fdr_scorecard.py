import pytest
from patternlab.engine import Engine
from patternlab.plugin_api import TestPlugin, TestResult, BytesView


class FakeTest(TestPlugin):
    def __init__(self, name, p_value, effect_sizes=None):
        self._name = name
        self._p = p_value
        self._effects = effect_sizes or {}

    def describe(self) -> str:
        return "fake test"

    def run(self, data: BytesView, params):
        passed = bool(self._p > params.get('pass_threshold', 0.05))
        return TestResult(
            test_name=self._name,
            passed=passed,
            p_value=self._p,
            category="statistical",
            p_values={},
            effect_sizes=self._effects,
            flags=[],
            metrics={},
        )


def test_bh_rejection_simple():
    e = Engine()
    # register two fake tests with distinct p-values
    e.register_test('t1', FakeTest('t1', 0.01))
    e.register_test('t2', FakeTest('t2', 0.2))

    out = e.analyze(b'\x00' * 4, {'tests': [{'name': 't1'}, {'name': 't2'}], 'fdr_q': 0.05})
    assert isinstance(out, dict)
    results = out['results']
    assert len(results) == 2
    res_map = {r['test_name']: r for r in results}
    assert res_map['t1']['fdr_rejected'] is True
    assert res_map['t2']['fdr_rejected'] is False
    assert out['scorecard']['failed_tests'] == 1


def test_bh_no_rejections():
    e = Engine()
    e.register_test('a', FakeTest('a', 0.1))
    e.register_test('b', FakeTest('b', 0.2))
    e.register_test('c', FakeTest('c', 0.3))

    out = e.analyze(b'\xFF' * 2, {'tests': [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}], 'fdr_q': 0.05})
    assert all(not r['fdr_rejected'] for r in out['results'])
    assert out['scorecard']['failed_tests'] == 0


def test_scorecard_mean_effect_and_distribution():
    e = Engine()
    e.register_test('t_small', FakeTest('t_small', 0.001, {'d': 0.2}))
    e.register_test('t_med', FakeTest('t_med', 0.02, {'d': 0.5}))
    e.register_test('t_none', FakeTest('t_none', 0.5, {}))

    out = e.analyze(
        b'\xAA' * 8,
        {'tests': [{'name': 't_small'}, {'name': 't_med'}, {'name': 't_none'}], 'fdr_q': 0.05},
    )
    sc = out['scorecard']
    # mean effect should be average of 0.2 and 0.5 => 0.35
    assert abs(sc['mean_effect_size'] - 0.35) < 1e-6
    assert sc['total_tests'] == 3
    assert sc['p_value_distribution']['count'] == 3
    hist = sc['p_value_distribution']['histogram']
    assert sum(hist.values()) == sc['p_value_distribution']['count']
def test_linear_complexity_excluded_from_fdr():
    from patternlab.plugins.linear_complexity import LinearComplexityTest

    e = Engine()
    # register the real linear_complexity plugin (diagnostic) and a significant fake test
    e.register_test('linear_complexity', LinearComplexityTest())
    e.register_test('t_sig', FakeTest('t_sig', 0.001))

    out = e.analyze(b'\x00' * 8, {'tests': [{'name': 'linear_complexity'}, {'name': 't_sig'}], 'fdr_q': 0.05})
    results = out['results']
    res_map = {r['test_name']: r for r in results}

    # linear_complexity should not contribute a p-value to FDR and should be marked diagnostic
    assert res_map['linear_complexity']['p_value'] is None
    assert res_map['linear_complexity']['fdr_rejected'] is False

    # the statistical fake test should be evaluated for FDR (and be rejected)
    assert res_map['t_sig']['p_value'] == 0.001
    assert res_map['t_sig']['fdr_rejected'] is True

    # scorecard counts only the statistical failures
    assert out['scorecard']['failed_tests'] == 1
def test_plugin_categories_and_fdr_scope():
    """Mini-test: diagnostic plugins must have p_value=None and be excluded from FDR; statistical ones included."""
    from patternlab.plugins import autocorrelation, fft_spectral, linear_complexity, monobit, block_frequency_test

    e = Engine()
    e.register_test('autocorrelation', autocorrelation.AutocorrelationTest())
    e.register_test('fft_spectral', fft_spectral.FFTSpectralTest())
    e.register_test('linear_complexity', linear_complexity.LinearComplexityTest())
    e.register_test('monobit', monobit.MonobitTest())
    e.register_test('block_frequency', block_frequency_test.BlockFrequencyTest())

    tests = [
        {'name': 'autocorrelation'},
        {'name': 'fft_spectral'},
        {'name': 'linear_complexity'},
        {'name': 'monobit'},
        {'name': 'block_frequency'},
    ]
    out = e.analyze(b'\x00' * 8, {'tests': tests, 'fdr_q': 0.05})

    results = out['results']
    res_map = {r['test_name']: r for r in results}

    # Diagnostic plugins should present p_value == None and not be FDR candidates
    assert res_map['linear_complexity']['p_value'] is None
    assert res_map['autocorrelation']['p_value'] is None
    assert res_map['fft_spectral']['p_value'] is None
    assert res_map['linear_complexity']['fdr_rejected'] is False

    # Statistical plugins should provide p_values and be counted in p-value distribution
    assert res_map['monobit']['p_value'] is not None
    assert res_map['block_frequency']['p_value'] is not None

    # Scorecard p-value distribution count must equal number of statistical tests included
    assert out['scorecard']['p_value_distribution']['count'] == 2
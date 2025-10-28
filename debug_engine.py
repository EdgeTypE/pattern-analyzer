from patternanalyzer.engine import Engine
from patternanalyzer.plugin_api import TestPlugin, TestResult

class ObsTest(TestPlugin):
    def describe(self): return "Observ"
    def run(self, data, params):
        _ = data.to_bytes()
        return TestResult(test_name="obs_test", passed=True, p_value=None)

e = Engine()
e.register_test("obs_test", ObsTest())
out = e.analyze(b"\x00\x01\x02", {"tests":[{"name":"obs_test","params":{}}]})
print("analyze returned:", repr(out))
import inspect, patternanalyzer.engine
src = inspect.getsource(patternanalyzer.engine)
print("\n--- source slice 1000..1320 ---")
for i, line in enumerate(src.splitlines(), start=1):
    if 1000 <= i <= 1320:
        print(f"{i:4d} | {line}")
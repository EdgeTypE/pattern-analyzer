# Plugin Developer Guide

Pattern Analyzer's power comes from its extensible plugin architecture. This guide explains how to create your own plugins.

## Core Concepts

There are three types of plugins, all inheriting from base classes defined in `patternanalyzer/plugin_api.py`:

1.  **`TransformPlugin`**: Modifies the input data before it is passed to the test plugins. Examples include XORing, decoding, or decryption.
2.  **`TestPlugin`**: The core analysis unit. It inspects the data and returns a `TestResult` object with findings.
3.  **`VisualPlugin`**: Generates a visual artifact (like an SVG or PNG) based on a `TestResult` from another plugin.

### Key Data Structures

- **`BytesView`**: A memory-efficient wrapper around the input data (`bytes` or `memoryview`). It provides helpful methods like `.bit_view()` to get a sequence of bits without extra copies.
- **`TestResult`**: A dataclass that holds the output of a `TestPlugin`. It includes fields like `test_name`, `passed`, `p_value`, and a `metrics` dictionary for detailed statistics.

## Creating a Simple Test Plugin

Let's create a new `TestPlugin` that checks if the data consists entirely of null bytes.

1.  **Create the Plugin File**

    Create a new file `patternanalyzer/plugins/all_zeros.py`:

    ```python
    from patternanalyzer.plugin_api import TestPlugin, TestResult, BytesView

    class AllZerosTest(TestPlugin):
        """A simple diagnostic test to check for all-zero data."""

        def describe(self) -> str:
            return "Checks if the data consists entirely of null bytes."

        def run(self, data: BytesView, params: dict) -> TestResult:
            # Get the raw bytes from the BytesView
            input_bytes = data.to_bytes()
            
            # Check if there are any non-zero bytes
            is_all_zeros = not any(input_bytes)
            
            # For a diagnostic test, we don't produce a p-value.
            # 'passed' is subjective; here we'll say it "passes" if it's NOT all zeros.
            return TestResult(
                test_name="all_zeros",
                passed=not is_all_zeros,
                p_value=None,  # This is a diagnostic, not statistical, test
                category="diagnostic",
                metrics={
                    "total_bytes": len(input_bytes),
                    "is_all_zeros": is_all_zeros
                }
            )
    ```

2.  **Register the Plugin**

    The easiest way to make your plugin discoverable is by adding an entry point to `pyproject.toml` under the `[project.entry-points."patternanalyzer.plugins"]` section.

    ```toml
    # In pyproject.toml
    [project.entry-points."patternanalyzer.plugins"]
    all_zeros = "patternanalyzer.plugins.all_zeros:AllZerosTest"
    # ... other plugins
    ```

    After adding the entry point, reinstall the package in editable mode for the changes to take effect:
    ```bash
    pip install -e .
    ```
    The Pattern Analyzer engine will now automatically discover and register your new plugin at startup.

## Supporting Streaming Analysis

For plugins that can process data in chunks, you can implement the streaming API by overriding the `update` and `finalize` methods. This is memory-efficient for large files.

- **`update(self, chunk: bytes, params: dict)`**: This method is called for each chunk of data from the stream. Your plugin should update its internal state here.
- **`finalize(self, params: dict) -> TestResult`**: Called after all chunks have been processed. This method should compute the final result based on the accumulated state and then reset the state for the next run.

See `patternanalyzer/plugins/monobit.py` for a simple example of a test that supports both batch (`run`) and streaming (`update`/`finalize`) modes.

## Writing Unit Tests

It's crucial to write tests for your new plugin. Add a new test file in the `tests/` directory, for example, `tests/test_all_zeros.py`.

```python
from patternanalyzer.plugins.all_zeros import AllZerosTest
from patternanalyzer.plugin_api import BytesView

def test_all_zeros_positive():
    plugin = AllZerosTest()
    data = BytesView(b'\x00\x00\x00\x00')
    result = plugin.run(data, {})
    assert result.passed is False
    assert result.metrics["is_all_zeros"] is True

def test_all_zeros_negative():
    plugin = AllZerosTest()
    data = BytesView(b'\x00\x01\x00\x00')
    result = plugin.run(data, {})
    assert result.passed is True
    assert result.metrics["is_all_zeros"] is False
```

Run the test suite to ensure your plugin works as expected:
```bash
pytest
```
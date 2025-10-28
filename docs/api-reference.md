# API Reference

This page provides a reference for the programmatic use of the Pattern Analyzer Python API. It is intended for developers who want to integrate Pattern Analyzer's analysis capabilities into their own applications.

## Core Components

The API revolves around a few key classes defined in `patternanalyzer.engine` and `patternanalyzer.plugin_api`.

### `Engine`

The `Engine` class is the main entry point for all analysis tasks.

```python
from patternanalyzer.engine import Engine

# Initialize the engine. This automatically discovers installed plugins.
engine = Engine()
```

#### `engine.analyze(input_bytes: bytes, config: dict) -> dict`

Performs a full analysis on a byte string.

- **`input_bytes`**: The binary data to analyze.
- **`config`**: A dictionary specifying the analysis pipeline (transforms, tests, settings).
- **Returns**: A dictionary containing the `results`, `scorecard`, and `meta` information.

**Example:**
```python
output = engine.analyze(
    b'\x00\x01\x02' * 100,
    config={"tests": [{"name": "monobit"}]}
)
```

#### `engine.analyze_stream(stream_iterable, config: dict) -> dict`

Performs analysis on a stream of data (an iterable of `bytes`). This is memory-efficient for large files. Only plugins that implement the streaming API (`update`/`finalize`) will run.

**Example:**
```python
def file_stream(path, chunk_size=4096):
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk

stream = file_stream("large_file.bin")
output = engine.analyze_stream(stream, config={"tests": [{"name": "monobit"}]})
```

#### `engine.get_available_tests() -> list[str]`

Returns a list of names of all registered test plugins.

### `BytesView`

A memory-efficient wrapper for binary data passed to plugins. It's the primary data type used within the `run` method of plugins.

```python
from patternanalyzer.plugin_api import BytesView

data = BytesView(b'\xAA\xBB\xCC')

# Get the data back as bytes
raw_bytes = data.to_bytes()

# Get a view of the data as a list of bits (0s and 1s)
bits = data.bit_view()
# bits will be [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, ...]
```

### `TestResult`

A dataclass used by `TestPlugin` instances to return their findings.

```python
from patternanalyzer.plugin_api import TestResult

# Example of creating a TestResult within a plugin
result = TestResult(
    test_name="my_custom_test",
    passed=True,
    p_value=0.98,
    category="statistical",
    metrics={"key_statistic": 123.45}
)```

## Full API Example

This example demonstrates initializing the engine, defining a custom analysis pipeline, and running the analysis.

```python
from patternanalyzer.engine import Engine
import json
import os

# --- 1. Setup ---
# Initialize the engine
engine = Engine()

# Prepare some sample data
# Highly non-random data (repeating pattern)
sample_data = b'\x10\x20\x30' * 1000

# --- 2. Configure the Analysis ---
# We want to apply a transform and then run a few specific tests.
analysis_config = {
    # Apply an XOR transform with key 0x42 first
    "transforms": [
        {
            "name": "xor_const", 
            "params": {"xor_value": 0x42}
        }
    ],
    # Run these tests on the transformed data
    "tests": [
        {"name": "monobit"},
        {"name": "runs"},
        {"name": "ecb_detector"}
    ],
    # Set a global significance level for FDR correction
    "fdr_q": 0.05,
    # Generate an HTML report
    "html_report": "api_report.html"
}

# --- 3. Run and Process Results ---
print("Starting analysis...")
output = engine.analyze(sample_data, analysis_config)
print("Analysis complete.")

# Save the full JSON report
with open("api_report.json", "w") as f:
    json.dump(output, f, indent=2)

# Print a summary from the scorecard
scorecard = output.get("scorecard", {})
print(f"\n--- Scorecard Summary ---")
print(f"Failed Tests (FDR Rejected): {scorecard.get('failed_tests')}")
print(f"Total Tests Run: {scorecard.get('total_tests')}")
print(f"HTML report generated at: {os.path.abspath('api_report.html')}")
```
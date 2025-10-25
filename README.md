# PatternLab

Binary pattern analysis framework for statistical testing and transformation of binary data.

## Features

- **Plugin Architecture**: Extensible system for transforms and statistical tests
- **XOR Transform**: Apply constant XOR transformation to binary data
- **Monobit Test**: Statistical frequency test for binary sequences
- **CLI Interface**: Command-line tool for easy analysis
- **Python API**: Programmatic access to all functionality

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd patternlab

# Install in development mode
pip install -e .
```

### Dependencies

- Python 3.10+
- click (for CLI)
- pytest (for testing)

## Usage

### Command Line Interface

Analyze a binary file:

```bash
# Basic analysis (writes JSON with top-level keys "results" and "scorecard")
patternlab analyze input.bin --out results.json

# With XOR constant transformation
patternlab analyze input.bin --out results.json --xor-value 255
```

Options:
- `input-file`: Path to binary file to analyze
- `--out`: Output JSON file (default: report.json)
- `--xor-value`: XOR value for transformation (0-255, default: 0)

CLI example — updated JSON output (file written to `results.json`; top-level schema shown below):

Top-level schema:

```json
{
  "results": [...],
  "scorecard": {...}
}
```

Full example output (file written to `results.json`):

```json
{
  "results": [
    {
      "test_name": "monobit",
      "passed": true,
      "p_value": 0.05,
      "p_values": {"overall": 0.05},
      "effect_sizes": {"overall": 0.8},
      "flags": [],
      "metrics": {"bit_count": 1000},
      "z_score": 1.96,
      "evidence": null,
      "fdr_rejected": false,
      "fdr_q": 0.05
    }
  ],
  "scorecard": {
    "failed_tests": 0,
    "mean_effect_size": 0.8,
    "p_value_distribution": {
      "count": 1,
      "mean": 0.05,
      "median": 0.05,
      "stdev": 0.0,
      "histogram": {"0-0.01": 0, "0.01-0.05": 0, "0.05-0.1": 1, "0.1-1.0": 0}
    },
    "total_tests": 1,
    "fdr_q": 0.05
  }
}
```

### Python API

```python
from patternlab.engine import Engine
from patternlab.plugins.xor_const import XOPlugin
from patternlab.plugins.monobit import MonobitTest
from patternlab.plugin_api import BytesView, serialize_testresult
import json

# Engine ve plugin kayıtları
engine = Engine()
engine.register_transform('xor_const', XOPlugin())
engine.register_test('monobit', MonobitTest())

# Veri analizi
with open('input.bin', 'rb') as f:
    data = f.read()

config = {'transforms': [{'name': 'xor_const', 'params': {'xor_value': 255}}], 'tests': [{'name': 'monobit', 'params': {}}]}
output = engine.analyze(data, config)

# `engine.analyze` fonksiyonu top-level bir dict döner:
# { "results": [...], "scorecard": {...} }
# TestResult'ları canonical JSON şemasına çevirmek için serialize_testresult kullanılmaktadır.
print(json.dumps(output, indent=2))
```

Örnek serializasyon (yeni TestResult şeması — CLI ve engine tarafından üretilen her bir sonuç bu şemaya uyar):
```json
{
  "test_name": "monobit",
  "passed": true,
  "p_value": 0.05,
  "p_values": {"overall": 0.05},
  "effect_sizes": {"overall": 0.8},
  "flags": ["flag1", "flag2"],
  "metrics": {"metric1": 123, "metric2": 456},
  "z_score": 1.96,
  "evidence": "Some evidence string",
  "fdr_rejected": false,
  "fdr_q": 0.05
}
```

Not: Eğer eski `details` alanı varsa, `serialize_testresult` fonksiyonu onu `metrics` içine birleştirir.

## Available Plugins

### Transform Plugins

- **xor_const**: Applies XOR transformation with constant value

### Test Plugins

- **monobit**: Monobit frequency test for random number generators

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_xor.py
```

## Project Structure

```
patternlab/
├── __init__.py              # Package initialization
├── plugin_api.py           # Plugin base classes and data structures
├── engine.py               # Main analysis engine
├── cli.py                  # Command line interface
└── plugins/
    ├── __init__.py
    ├── xor_const.py        # XOR transform plugin
    └── monobit.py          # Monobit test plugin
tests/
├── test_xor.py
└── test_monobit.py
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## Requirements

- Python 3.10 or higher
- No external dependencies beyond standard library (except for development)

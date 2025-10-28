# Getting Started

This guide will walk you through the basic steps to set up Pattern Analyzer and perform your first analysis.

## Prerequisites

- Python 3.10 or newer.
- `git` for cloning the repository.

## Installation

First, clone the repository and set up a Python virtual environment.

```bash
# Clone the repository
git clone https://github.com/edgetype/pattern-analyzer.git
cd pattern-analyzer

# Create and activate a virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

# Install the project in editable mode with all optional dependencies
pip install -e .[test,ml,ui]
```

This command installs Pattern Analyzer and all dependencies required for the user interfaces, machine learning plugins, and running tests.

## Running Your First Analysis (CLI)

The Command-Line Interface (CLI) is the quickest way to analyze a file. Let's analyze the provided `test.bin` file.

```bash
# Run analysis on a file and save the output to report.json
patternanalyzer analyze test.bin --out report.json
```

After the command completes, a `report.json` file will be created in your directory. It contains a detailed breakdown of the results from all default tests.

```json
{
  "results": [
    {
      "test_name": "monobit",
      "passed": true,
      "p_value": 0.53,
      "...": "..."
    }
  ],
  "scorecard": {
    "failed_tests": 0,
    "...": "..."
  },
  "meta": {
    "...": "..."
  }
}
```

## Using the Python API

For more advanced use cases, you can integrate Pattern Analyzer directly into your Python scripts.

Create a file named `example.py` with the following content:

```python
from patternanalyzer.engine import Engine
import json

# 1. Initialize the analysis engine
engine = Engine()

# 2. Define the data to be analyzed
data_bytes = b'\x55\xAA' * 128  # A simple alternating pattern

# 3. Create a configuration for the analysis
#    We will run two simple tests: 'monobit' and 'runs'
config = {
    "tests": [
        {"name": "monobit"},
        {"name": "runs"}
    ]
}

# 4. Run the analysis
output = engine.analyze(data_bytes, config)

# 5. Print the scorecard
print("Analysis Scorecard:")
print(json.dumps(output.get('scorecard'), indent=2))
```

Run the script from your terminal:

```bash
python example.py
```

## Launching the Web UI

Pattern Analyzer includes a user-friendly web interface built with Streamlit for interactive analysis.

To start it, run the following command in your terminal:

```bash
streamlit run app.py
```

Now, open your web browser and navigate to the local URL displayed in the terminal (usually `http://localhost:8501`). You can upload files, select tests, and view results interactively.
# Configuration Examples

This directory contains example configuration files for PatternLab in both `JSON` and `YAML` formats. These files demonstrate how to customize an analysis pipeline.

## Files

- **`example.json`**: An example configuration using JSON syntax.
- **`example.yml`**: An equivalent example using YAML syntax.

## Configuration Structure

You can use a configuration file with the CLI (`-c` or `--config` flag) or pass a dictionary with the same structure to the `engine.analyze()` method in the Python API.

The main top-level keys are:

-   `transforms`: A list of data transformation plugins to apply sequentially before analysis. Each item can be a simple string (the plugin name) or a dictionary specifying a `name` and `params`.
-   `tests`: A list of test plugins to run on the (potentially transformed) data. The structure is the same as for `transforms`.
-   `fdr_q`: (Optional) A float between 0 and 1 specifying the significance level (q-value) for the False Discovery Rate (FDR) correction. This helps control for false positives when running multiple tests. Defaults to `0.05`.
-   `html_report`: (Optional) A file path where a standalone HTML report will be generated.
-   `log_path`: (Optional) A file path where detailed, structured (JSONL) logs will be written during the analysis.

### Example Usage (CLI)

You can run an analysis using one of the example configuration files like this:

```bash
# Using the YAML configuration
patternlab analyze my_data.bin --config docs/configs/example.yml

# Using the JSON configuration
patternlab analyze my_data.bin --config docs/configs/example.json
```
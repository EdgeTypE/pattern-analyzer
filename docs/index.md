# Welcome to PatternLab

This site provides comprehensive documentation for the PatternLab framework, covering user guides, API references, and plugin development.

PatternLab is a powerful, plugin-based framework designed for the analysis of binary data. Whether you're a security researcher, a data scientist, or a developer, PatternLab provides the tools to dissect binary files, detect patterns, and assess randomness through a suite of statistical and analytical tools.

## Quick Navigation

- **[Getting Started](./getting-started.md)**: A quick-start guide to install PatternLab and run your first analysis.
- **[User Guide](./user-guide.md)**: Detailed instructions on using the CLI, Web UI, and configuration files.
- **[Plugin Developer Guide](./plugin-developer-guide.md)**: Learn how to create your own tests, transforms, and visualizers.
- **[API Reference](./api-reference.md)**: A reference for using PatternLab programmatically in your own Python scripts.
- **[Test Reference](./test-reference.md)**: A detailed catalog of all built-in analysis plugins.
- **[Configuration Examples](./configs/README.md)**: See examples of `YAML` and `JSON` configuration files.

## Running the Documentation Locally

To browse this documentation site on your local machine, ensure you have MkDocs and the Material theme installed.

```bash
# Install required packages (preferably in a virtual environment)
pip install mkdocs mkdocs-material

# Serve the documentation site
mkdocs serve
```

This will start a local web server, and you can view the site by navigating to `http://127.0.0.1:8000` in your browser.
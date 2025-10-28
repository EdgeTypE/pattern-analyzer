# Contributing to Pattern Analyzer

First off, thank you for considering contributing to Pattern Analyzer! We welcome any contributions, from fixing a typo in the documentation to implementing a brand-new analysis plugin.

This document provides guidelines for contributing to the project.

## Code of Conduct

This project and everyone participating in it is governed by the [Pattern Analyzer Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

There are many ways to contribute to Pattern Analyzer:

- **Reporting Bugs**: If you find a bug, please open an issue and provide detailed steps to reproduce it.
- **Suggesting Enhancements**: Have an idea for a new feature or a new plugin? Open an issue to discuss it.
- **Improving Documentation**: If you find parts of the documentation unclear or incomplete, feel free to submit a pull request with your improvements.
- **Writing Code**: Contribute by fixing bugs, improving existing features, or adding new plugins.

## Your First Code Contribution

Unsure where to begin? A great place to start is by looking for issues tagged with `good first issue` or `help wanted`.

### Development Setup

To get your development environment ready, please follow these steps:

1.  **Fork the repository** on GitHub.

2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/edgetype/pattern-analyzer.git
    cd pattern-analyzer
    ```

3.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    ```

4.  **Activate the virtual environment**:
    -   On Windows:
        ```powershell
        .venv\Scripts\Activate.ps1
        ```
    -   On macOS and Linux:
        ```bash
        source .venv/bin/activate
        ```

5.  **Install dependencies** in editable mode. This is crucial as it allows your local code changes to be immediately reflected when you run the `patternanalyzer` command.
    ```bash
    pip install -e .[test,ml,ui]
    ```

### Pull Request Process

1.  **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/my-awesome-plugin-or-something-else
    ```

2.  **Make your changes**. Write clean, readable code and follow the existing code style.

3.  **Add tests** for your changes. This is very important.
    -   If you're fixing a bug, add a test that fails without your change and passes with it.
    -   If you're adding a new feature, add tests that cover its functionality.
    -   Tests are located in the `tests/` directory.

4.  **Run the full test suite** to ensure everything is working correctly:
    ```bash
    pytest
    ```

5.  **Update the documentation** if necessary.
    -   If you've added a new plugin, add it to the `docs/test-reference.md` file.
    -   If you've changed the CLI or API, update the relevant sections in the `docs/` folder.

6.  **Commit your changes** with a clear and descriptive commit message.

7.  **Push your branch** to your fork on GitHub:
    ```bash
    git push origin feature/my-awesome-plugin
    ```

8.  **Open a Pull Request** to the `main` branch of the original repository.
    -   Provide a clear title and a detailed description of your changes.
    -   If your PR addresses an existing issue, link it by including `Closes #123` in the description.

Your pull request will be reviewed, and we'll provide feedback. Thank you for your contribution!

### A Note on Plugin Development

One of the most valuable ways to contribute is by creating new plugins. The framework is designed to make this easy. For a detailed guide on creating your own tests, transforms, or visualizers, please see our **[Plugin Developer Guide](./docs/plugin-developer-guide.md)**.
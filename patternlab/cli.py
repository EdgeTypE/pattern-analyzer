"""Command line interface for PatternLab."""

import json
import click
import os
from .engine import Engine
from .plugin_api import serialize_testresult

try:
    import yaml  # optional dependency for YAML config files
except Exception:
    yaml = None


@click.group()
@click.version_option()
def cli():
    """PatternLab - Binary pattern analysis framework."""
    pass


def _normalize_tests_entry(t):
    """Normalize a single test entry which may be either a string or a dict."""
    if isinstance(t, str):
        return {'name': t, 'params': {}}
    if isinstance(t, dict):
        return {'name': t.get('name'), 'params': t.get('params', {})}
    raise ValueError("Invalid test entry type")


def _normalize_transforms_entry(t):
    """Normalize a single transform entry which may be either a string or a dict."""
    if isinstance(t, str):
        return {'name': t, 'params': {}}
    if isinstance(t, dict):
        return {'name': t.get('name'), 'params': t.get('params', {})}
    raise ValueError("Invalid transform entry type")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--out', '-o', 'output_file', type=click.Path(),
              default='report.json', help='Output JSON file path')
@click.option('--xor-value', type=int, default=0,
              help='XOR value for transformation (0-255)')
@click.option('--config', '-c', 'config_path', type=click.Path(exists=True), default=None,
              help='Path to YAML or JSON configuration file specifying tests/transforms')
@click.option('--default-visuals', 'default_visuals', type=str, default=None,
              help='Default visuals settings as JSON string')
@click.option('--artefact-dir', 'artefact_dir', type=click.Path(), default=None,
              help='Directory to write visual artefacts (writes files instead of inline base64)')
@click.option('--html-report', 'html_report', type=click.Path(), default=None,
              help='Path to write minimal HTML report')
def analyze(input_file, output_file, xor_value, config_path, default_visuals, artefact_dir, html_report):
    """Analyze binary file for patterns.

    Supports optional YAML or JSON configuration files. When no config is provided,
    a sensible default wide test-set is executed.
    """
    try:
        # Read input file
        with open(input_file, 'rb') as f:
            input_bytes = f.read()

        # Default wide test set
        default_tests = [
            "monobit",
            "runs",
            "block_frequency",
            "serial",
            "fft_spectral",
            "autocorrelation",
            "linear_complexity",
        ]

        file_conf = {}
        if config_path:
            # Load YAML if extension suggests yaml/yml and yaml lib available; otherwise JSON
            _, ext = os.path.splitext(config_path.lower())
            with open(config_path, 'r', encoding='utf-8') as cf:
                if ext in ('.yaml', '.yml'):
                    if yaml is None:
                        raise click.BadParameter("PyYAML is required to load YAML config files; install 'pyyaml' or use JSON")
                    file_conf = yaml.safe_load(cf) or {}
                else:
                    # assume JSON
                    file_conf = json.load(cf) or {}

        # Ensure structure is normalized for Engine.analyze
        transforms_conf = file_conf.get('transforms', [])
        tests_conf = file_conf.get('tests', None)

        # If tests not provided in config, use default wide set
        if tests_conf is None:
            tests_conf = default_tests

        # Normalize entries (allow strings or dicts in config)
        transforms = [_normalize_transforms_entry(t) for t in transforms_conf]
        tests = [_normalize_tests_entry(t) for t in tests_conf]

        # Honor xor_value CLI flag by appending the transform (CLI flag takes precedence and is additive)
        if xor_value:
            transforms.append({'name': 'xor_const', 'params': {'xor_value': xor_value}})

        # Allow other top-level config options (e.g., fdr_q, visuals) to pass-through
        merged_config = {
            'transforms': transforms,
            'tests': tests,
        }
        for k in ('fdr_q', 'visuals'):
            if k in file_conf:
                merged_config[k] = file_conf[k]

        # If CLI provided default_visuals JSON, parse and set as visuals (CLI flag overrides file)
        if default_visuals:
            try:
                merged_config['visuals'] = json.loads(default_visuals)
            except Exception as e:
                raise click.BadParameter(f"--default-visuals must be valid JSON: {e}")

        # If artefact_dir provided via CLI, pass it through to engine (engine will write files there)
        if artefact_dir:
            merged_config['artefact_dir'] = artefact_dir
        # If html_report provided via CLI, request engine to write minimal HTML report
        if html_report:
            merged_config['html_report'] = html_report

        # Run analysis
        engine = Engine()
        output = engine.analyze(input_bytes, merged_config)

        # Write output directly as JSON following the new schema
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        click.echo(f"Analysis complete. Results written to {output_file}")

    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
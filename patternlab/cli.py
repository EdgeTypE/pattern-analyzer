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
@click.option('--discover', is_flag=True, default=False,
              help='Run discovery/transform search instead of standard analysis')
@click.option('--config', '-c', 'config_path', type=click.Path(exists=True), default=None,
              help='Path to YAML or JSON configuration file specifying tests/transforms')
@click.option('--profile', 'profile', type=click.Choice(['quick','full','nist','crypto'], case_sensitive=True), default=None,
              help='Use a preset profile of tests/transforms (overrides tests/transforms in config)')
@click.option('--budget-ms', 'budget_ms', type=int, default=None,
              help='Overall analysis time budget in milliseconds; remaining tests will be skipped when exhausted')
@click.option('--default-visuals', 'default_visuals', type=str, default=None,
              help='Default visuals settings as JSON string')
@click.option('--artefact-dir', 'artefact_dir', type=click.Path(), default=None,
              help='Directory to write visual artefacts (writes files instead of inline base64)')
@click.option('--html-report', 'html_report', type=click.Path(), default=None,
              help='Path to write minimal HTML report')
@click.option('--log-level', 'log_level', type=click.Choice(['DEBUG','INFO','WARNING','ERROR'], case_sensitive=True), default='INFO',
              help='Set logging level for patternlab logger and test debug output')
@click.option('--sandbox-mode', 'sandbox_mode', is_flag=True, default=False,
              help='Run tests in isolated subprocess per test (sandbox)')
@click.option('--sandbox-mem', 'sandbox_mem_mb', type=int, default=None,
              help='Memory limit for sandboxed plugin processes in MB (best-effort; Unix-only)')
def analyze(input_file, output_file, xor_value, discover, config_path, profile, budget_ms, default_visuals, artefact_dir, html_report, log_level, sandbox_mode, sandbox_mem_mb):
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
            'log_level': log_level,
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
 
        # Inject profile/budget if provided via CLI. Profile overrides tests/transforms from file.
        engine = Engine()
        if profile:
            prof = engine.get_profile(profile)
            if prof:
                # Normalize profile entries and override tests/transforms
                prof_transforms = prof.get('transforms', [])
                prof_tests = prof.get('tests', [])
                merged_config['transforms'] = [_normalize_transforms_entry(t) for t in prof_transforms]
                merged_config['tests'] = [_normalize_tests_entry(t) for t in prof_tests]
                merged_config['profile'] = profile
        if budget_ms is not None:
            merged_config['budget_ms'] = int(budget_ms)
 
        # Run analysis
        if discover:
            output = engine.discover(input_bytes, merged_config)
        else:
            output = engine.analyze(input_bytes, merged_config)

        # Write output directly as JSON following the new schema
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        click.echo(f"Analysis complete. Results written to {output_file}")

    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--calibrate', 'calibrate', is_flag=True, required=True, help='Run p-value calibration routine (required for this subcommand)')
@click.option('--samples', 'samples', type=int, default=1000, help='Number of streams/samples to generate for calibration')
@click.option('--seed', 'seed', type=int, default=None, help='Random seed for generator (deterministic)')
@click.option('--out-dir', 'out_dir', type=click.Path(), default='bench_artifacts', help='Directory to write artefacts (plots, JSON summary)')
@click.option('--profile', 'profile', type=str, default='nist', help="Test profile to calibrate (defaults to 'nist')")
def bench(calibrate, samples, seed, out_dir, profile):
    """Run benchmark helpers such as p-value calibration and produce KS / QQ artefacts.

    Usage:
      python -m patternlab.cli bench --calibrate [--samples N] [--seed S] [--out-dir DIR] [--profile PROFILE]
    """
    try:
        if not calibrate:
            click.echo("The --calibrate flag is required for the bench subcommand", err=True)
            raise click.Abort()

        # Lazy imports for calibration utilities and plotting
        from .engine import Engine
        from .plugin_api import BytesView
        from .validation import p_value_calibration as pvc

        # Prepare output directory
        os.makedirs(out_dir, exist_ok=True)

        engine = Engine()
        prof = engine.get_profile(profile) or {}
        tests_conf = prof.get("tests") or []

        # Normalize tests (allow list of strings or dict entries)
        test_names = []
        for t in tests_conf:
            if isinstance(t, str):
                test_names.append(t)
            elif isinstance(t, dict):
                test_names.append(t.get("name"))
        # If profile empty, fall back to engine's available tests
        if not test_names:
            test_names = engine.get_available_tests()

        # Generate streams once for determinism and performance
        stream_length = 1024
        streams = pvc.generate_streams(count=int(samples), length=stream_length, mode="aes_ctr", seed=seed)

        summary = {"tests": {}, "meta": {"profile": profile, "samples": int(samples), "seed": seed}}

        # Try to import matplotlib for PNG output; fall back to SVG text if unavailable
        try:
            import matplotlib.pyplot as plt  # type: ignore
            has_plt = True
        except Exception:
            has_plt = False

        for test_name in test_names:
            safe_name = str(test_name).replace(" ", "_") if test_name else "unknown"
            test_entry = {"status": "skipped", "reason": None}
            if test_name not in engine._tests:
                test_entry["reason"] = "test_not_registered"
                summary["tests"][test_name] = test_entry
                click.echo(f"Skipping {test_name}: not registered in engine")
                continue

            plugin = engine._tests[test_name]
            params = {}

            def _run_one(bts: bytes):
                try:
                    bv = BytesView(bts)
                    res = plugin.safe_run(bv, params) if hasattr(plugin, "safe_run") else plugin.run(bv, params)
                    if isinstance(res, dict) and res.get("status") == "error":
                        return 1.0
                    # res may be TestResult
                    p = getattr(res, "p_value", None)
                    if p is None:
                        return 1.0
                    return float(p)
                except Exception:
                    return 1.0

            # Compute p-values for all streams
            p_values = pvc.compute_pvalues_from_streams(streams, _run_one)
            theoretical, empirical = pvc.qq_data(p_values)
            ks = pvc.ks_test_uniform(p_values)

            # Save KS JSON per-test and store in summary
            test_entry = {
                "status": "completed",
                "num_streams": len(p_values),
                "ks": ks,
            }

            # Write QQ plot (prefer PNG if matplotlib available)
            qq_fname_png = os.path.join(out_dir, f"qq_{safe_name}.png")
            qq_fname_svg = os.path.join(out_dir, f"qq_{safe_name}.svg")
            ks_fname = os.path.join(out_dir, f"ks_{safe_name}.json")
            try:
                if has_plt:
                    plt.figure(figsize=(4, 4))
                    plt.scatter(theoretical, empirical, s=6)
                    plt.plot([0, 1], [0, 1], color="red", linestyle="--")
                    plt.xlabel("Theoretical quantiles")
                    plt.ylabel("Empirical quantiles")
                    plt.title(f"QQ {safe_name}")
                    plt.tight_layout()
                    plt.savefig(qq_fname_png)
                    plt.close()
                    test_entry["qq_plot"] = qq_fname_png
                else:
                    # Minimal SVG fallback
                    w, h = 400, 400
                    points = []
                    for tx, ex in zip(theoretical, empirical):
                        x = 20 + int(tx * (w - 40))
                        y = h - (20 + int(ex * (h - 40)))
                        points.append(f"{x},{y}")
                    svg_lines = [
                        '<?xml version="1.0" encoding="utf-8"?>',
                        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
                        '<rect width="100%" height="100%" fill="white"/>',
                        '<polyline points="' + " ".join(points) + '" fill="none" stroke="black" stroke-width="1"/>',
                        '<line x1="20" y1="' + str(h-20) + '" x2="' + str(w-20) + '" y2="20" stroke="red" stroke-dasharray="4"/>',
                        f'<text x="10" y="15" font-size="12">QQ {safe_name}</text>',
                        "</svg>",
                    ]
                    with open(qq_fname_svg, "w", encoding="utf-8") as sf:
                        sf.write("\n".join(svg_lines))
                    test_entry["qq_plot"] = qq_fname_svg
            except Exception as e:
                test_entry.setdefault("errors", []).append(f"plot_error:{e}")

            # write ks json
            try:
                with open(ks_fname, "w", encoding="utf-8") as kf:
                    json.dump({"ks": ks, "num_streams": len(p_values)}, kf, indent=2)
                test_entry["ks_artifact"] = ks_fname
            except Exception as e:
                test_entry.setdefault("errors", []).append(f"ks_write_error:{e}")

            summary["tests"][test_name] = test_entry
            click.echo(f"{test_name}: KS p-value = {ks.get('p_value'):.6g}")

        # overall summary metrics
        total = len(summary["tests"])
        pass_count = sum(1 for t in summary["tests"].values() if t.get("ks", {}).get("p_value", 0) > 0.05)
        summary["overall"] = {"total_tests": total, "ks_p_gt_0_05": pass_count}

        # write summary JSON
        summary_path = os.path.join(out_dir, "bench_summary.json")
        try:
            with open(summary_path, "w", encoding="utf-8") as sf:
                json.dump(summary, sf, indent=2)
        except Exception as e:
            click.echo(f"Failed to write summary JSON: {e}", err=True)
            raise click.Abort()

        click.echo(f"Calibration complete. Summary written to {summary_path}")
    except Exception as e:
        click.echo(f"bench failed: {e}", err=True)
        raise click.Abort()
@cli.command()
@click.option('--host', 'host', default='127.0.0.1', help='Host to bind the UI server to')
@click.option('--port', 'port', default=8000, type=int, help='Port for the UI server')
@click.option('--reload', 'reload', is_flag=True, default=False, help='Enable auto-reload (development only)')
def serve_ui(host, port, reload):
    """Serve the self-hosted frontend UI together with the API using uvicorn.

    Serves the FastAPI app which already mounts the static UI at /ui.
    """
    try:
        click.echo(f"Starting PatternLab UI at http://{host}:{port}/")
        # Lazy import uvicorn so CLI can be used without the optional dependency installed.
        try:
            import uvicorn  # type: ignore
        except Exception:
            # Provide a clear actionable error via Click
            raise click.ClickException(
                "uvicorn is required to run 'serve-ui'.\n"
                "Install it with: pip install \"uvicorn[standard]\"\n"
                "Or run the server manually: python -m uvicorn patternlab.api:app --host {host} --port {port}".format(host=host, port=port)
            )
        # Use module path so uvicorn picks up patternlab.api:app
        uvicorn.run("patternlab.api:app", host=host, port=port, reload=reload)
    except click.ClickException:
        # Let Click handle this exception type (it will print the message)
        raise
    except Exception as e:
        click.echo(f"serve-ui failed: {e}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
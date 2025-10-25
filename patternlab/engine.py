"""PatternLab analysis engine."""
 
import importlib.metadata
from typing import Dict, Any, List, Tuple
from .plugin_api import BytesView, TestResult, TransformPlugin, TestPlugin, VisualPlugin, serialize_testresult
import base64
import uuid
import os
import math
import statistics
import time
import json
import datetime
import sys
import platform
import hashlib
 
 
class Engine:
    """Main analysis engine for PatternLab."""
 
    def __init__(self):
        self._transforms: Dict[str, TransformPlugin] = {}
        self._tests: Dict[str, TestPlugin] = {}
        self._visuals: Dict[str, VisualPlugin] = {}
        self._discover_plugins()
 
    def _discover_plugins(self):
        """Discover plugins via entry points."""
        # Register built-in plugins
        from .plugins.xor_const import XOPlugin
        from .plugins.monobit import MonobitTest

        self.register_transform('xor_const', XOPlugin())
        self.register_test('monobit', MonobitTest())

        # Register known bundled Visual plugins (optional)
        try:
            from .plugins.fft_placeholder import FFTPlaceholder
            self.register_visual('fft_placeholder', FFTPlaceholder())
        except Exception:
            # ignore if bundled visual plugin cannot be imported for any reason
            pass

        # Load plugins published via entry points (group: 'patternlab.plugins')
        import importlib.metadata as im
        for ep in im.entry_points(group='patternlab.plugins'):
            cls = ep.load()
            if issubclass(cls, TransformPlugin):
                self.register_transform(ep.name, cls())
            elif issubclass(cls, TestPlugin):
                self.register_test(ep.name, cls())
            elif issubclass(cls, VisualPlugin):
                # Entry point class implements VisualPlugin
                self.register_visual(ep.name, cls())
 
    def register_transform(self, name: str, plugin: TransformPlugin):
        """Register a transform plugin."""
        self._transforms[name] = plugin

    def register_test(self, name: str, plugin: TestPlugin):
        """Register a test plugin."""
        self._tests[name] = plugin

    def register_visual(self, name: str, plugin: VisualPlugin):
        """Register a visual plugin."""
        self._visuals[name] = plugin
 
    def _benjamini_hochberg(self, p_values: List[float], q: float) -> List[bool]:
        """Perform Benjamini–Hochberg FDR correction.
 
        Returns a list of booleans indicating which hypotheses are rejected (significant).
        """
        m = len(p_values)
        if m == 0:
            return []
        # Pair p-values with original indices
        indexed = sorted(enumerate(p_values), key=lambda x: x[1])
        rejected = [False] * m
        # Find the largest k such that p_(k) <= (k/m) * q (1-based k)
        max_k = 0
        for rank, (idx, p) in enumerate(indexed, start=1):
            if p <= (rank / m) * q:
                max_k = rank
        if max_k == 0:
            return rejected
        # Mark all with rank <= max_k as rejected
        for rank, (idx, p) in enumerate(indexed, start=1):
            if rank <= max_k:
                rejected[idx] = True
        return rejected
 
    def _pvalue_stats(self, p_values: List[float]) -> Dict[str, Any]:
        """Return simple statistics and a small histogram for p-values distribution."""
        if not p_values:
            return {"count": 0, "mean": None, "median": None, "stdev": None, "histogram": {}}
        cnt = len(p_values)
        mean = statistics.mean(p_values)
        median = statistics.median(p_values)
        stdev = statistics.pstdev(p_values) if cnt > 1 else 0.0
        # simple buckets
        buckets = {"0-0.01": 0, "0.01-0.05": 0, "0.05-0.1": 0, "0.1-1.0": 0}
        for p in p_values:
            if p < 0.01:
                buckets["0-0.01"] += 1
            elif p < 0.05:
                buckets["0.01-0.05"] += 1
            elif p < 0.1:
                buckets["0.05-0.1"] += 1
            else:
                buckets["0.1-1.0"] += 1
        return {"count": cnt, "mean": mean, "median": median, "stdev": stdev, "histogram": buckets}
 
    def analyze(self, input_bytes: bytes, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze input bytes using registered plugins and perform FDR + scorecard.
 
        config format:
        {
            'transforms': [{'name': 'xor_const', 'params': {'xor_value': 55}}],
            'tests': [{'name': 'monobit', 'params': {}}],
            'fdr_q': 0.05  # optional, default 0.05
        }
 
        Returns a dict with 'results' (serialized) and 'scorecard'.
        """
        # Normalize input
        data = BytesView(input_bytes)
 
        # Apply configured transforms in sequence
        for tconf in config.get('transforms', []):
            t = self._transforms[tconf['name']]
            try:
                data = t.run(data, tconf.get('params', {}))
            except Exception as e:
                # If a transform fails, report the error and abort analysis.
                return {
                    "results": [
                        {
                            "transform_name": tconf.get("name"),
                            "status": "error",
                            "details": str(e),
                        }
                    ],
                    "scorecard": {
                        "failed_tests": 0,
                        "mean_effect_size": None,
                        "p_value_distribution": {"count": 0, "mean": None, "median": None, "stdev": None, "histogram": {}},
                        "total_tests": 0,
                        "fdr_q": float(config.get("fdr_q", 0.05)),
                    },
                }
 
        # Determine tests to run: use provided list or all registered tests
        tests_conf = config.get('tests') or [{'name': n, 'params': {}} for n in self._tests]
 
        # Run tests but honor TestPlugin.requires: if required input not available, skip the test
        raw_results: List[object] = []  # elements are either TestResult or dict indicating skipped
        for c in tests_conf:
            tp = self._tests[c['name']]
            reqs = getattr(tp, 'requires', []) or []
            missing_reqs: List[str] = []
            # Lazy caches for data views that may be expensive
            _bits_cached = None
            for req in reqs:
                if req == 'bits':
                    try:
                        if _bits_cached is None:
                            _bits_cached = data.bit_view()
                    except Exception:
                        missing_reqs.append('bits')
                elif req == 'bytes':
                    try:
                        _ = data.to_bytes()
                    except Exception:
                        missing_reqs.append('bytes')
                elif req == 'text':
                    if data.text_view() is None:
                        missing_reqs.append('text')
                else:
                    # Unknown requirement: check attribute presence on BytesView
                    if not hasattr(data, req):
                        missing_reqs.append(req)
            if missing_reqs:
                reason = (
                    f"Required input '{missing_reqs[0]}' not available"
                    if len(missing_reqs) == 1
                    else f"Required inputs {missing_reqs} not available"
                )
                raw_results.append({"test_name": c['name'], "status": "skipped", "reason": reason})
            else:
                # Prepare lightweight observability measurements for this test invocation.
                try:
                    bytes_processed = len(data.to_bytes())
                except Exception:
                    bytes_processed = None

                # run the test using the plugin's safe_run wrapper (if available)
                # while measuring execution time (ms).
                start = time.perf_counter()
                res = tp.safe_run(data, c.get('params', {})) if hasattr(tp, "safe_run") else tp.run(data, c.get('params', {}))
                end = time.perf_counter()
                duration_ms = (end - start) * 1000.0

                if isinstance(res, TestResult):
                    # Attach observability fields to the TestResult (plugins are allowed to
                    # override if they set these themselves).
                    try:
                        # only set if not already provided by the plugin
                        if getattr(res, "time_ms", None) is None:
                            res.time_ms = duration_ms
                    except Exception:
                        res.time_ms = duration_ms
                    try:
                        if getattr(res, "bytes_processed", None) is None:
                            res.bytes_processed = bytes_processed
                    except Exception:
                        res.bytes_processed = bytes_processed

                    raw_results.append(res)
                elif isinstance(res, dict) and res.get("status") == "error":
                    # normalize the error into the same skipped/skipped-like dict shape used elsewhere
                    raw_results.append({"test_name": c['name'], "status": "error", "reason": res.get("reason")})
                else:
                    # fallback: append whatever the plugin returned
                    raw_results.append(res)
 
        # Extract primary p-values for FDR correction.
        # Only include tests that provide a p_value (not None) AND have category == "statistical".
        q = float(config.get('fdr_q', 0.05))
        p_values: List[float] = []
        for r in raw_results:
            if isinstance(r, TestResult) and r.p_value is not None and getattr(r, "category", None) == "statistical":
                p_values.append(r.p_value)
        
        rejected = self._benjamini_hochberg(p_values, q)
 
        # Serialize results and attach FDR info
        serialized_results: List[Dict[str, Any]] = []
        all_effects: List[float] = []
        visuals_conf = config.get('visuals', {})  # optional mapping plugin_name -> params
        # Map rejected flags back to test entries that actually produced p-values
        p_idx = 0
        for r in raw_results:
            if isinstance(r, TestResult):
                s = serialize_testresult(r)
                s['status'] = 'completed'
                # Only TestResult objects that contributed a p-value to the FDR (p_value not None
                # and category == "statistical") should be mapped to the `rejected` list.
                if r.p_value is not None and getattr(r, "category", None) == "statistical":
                    s['fdr_rejected'] = bool(rejected[p_idx]) if p_idx < len(rejected) else False
                    p_idx += 1
                else:
                    s['fdr_rejected'] = False
                s['fdr_q'] = q

                # Expose observability fields in the serialized result when present on the TestResult
                s['time_ms'] = getattr(r, "time_ms", None)
                s['bytes_processed'] = getattr(r, "bytes_processed", None)

                # Simple JSONL logger: if user provided config['log_path'], append a line per test
                log_path = config.get("log_path")
                if log_path:
                    try:
                        log_entry = {
                            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                            "test_name": s.get("test_name"),
                            "status": s.get("status"),
                            "time_ms": s.get("time_ms"),
                            "bytes_processed": s.get("bytes_processed"),
                        }
                        with open(log_path, "a", encoding="utf-8") as lf:
                            lf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                    except Exception:
                        # never fail the analysis because logging failed
                        pass

                # Attach visual artifacts produced by registered VisualPlugins.
                visuals_artifacts: Dict[str, Dict[str, str]] = {}
                artefact_dir = config.get('artefact_dir')
                for vname, vplugin in self._visuals.items():
                    try:
                        vparams = visuals_conf.get(vname, {})
                        out_bytes = vplugin.render(r, vparams)
                        if isinstance(out_bytes, (bytes, bytearray)):
                            mime = vparams.get('mime', 'image/svg+xml')
                            if artefact_dir:
                                # write bytes to file under artefact_dir and return path in JSON
                                try:
                                    os.makedirs(artefact_dir, exist_ok=True)
                                    # choose extension based on mime
                                    if mime == 'image/svg+xml':
                                        ext = 'svg'
                                    elif 'png' in mime:
                                        ext = 'png'
                                    elif 'jpeg' in mime or 'jpg' in mime:
                                        ext = 'jpg'
                                    else:
                                        ext = 'bin'
                                    safe_name = str(s.get('test_name') or 'visual').replace(" ", "_")
                                    fname = f"{safe_name}_{vname}_{uuid.uuid4().hex}.{ext}"
                                    path = os.path.join(artefact_dir, fname)
                                    with open(path, "wb") as wf:
                                        wf.write(bytes(out_bytes))
                                    visuals_artifacts[vname] = {'mime': mime, 'path': path}
                                except Exception as e:
                                    # if writing fails, propagate to outer handler to mark result as error
                                    raise
                            else:
                                # fallback: embed as base64 data URI (existing behaviour)
                                data_b64 = base64.b64encode(bytes(out_bytes)).decode('ascii')
                                visuals_artifacts[vname] = {'mime': mime, 'data_base64': data_b64}
                    except Exception as e:
                        # If a visual plugin fails for this result, mark this result as an error
                        # and include the exception details. Stop attempting other visuals for this result.
                        s['status'] = 'error'
                        s['details'] = str(e)
                        visuals_artifacts = {}
                        break
                if visuals_artifacts:
                    s['visuals'] = visuals_artifacts
 
                serialized_results.append(s)
                # collect effect sizes values if present
                if isinstance(r.effect_sizes, dict):
                    for v in r.effect_sizes.values():
                        try:
                            all_effects.append(float(v))
                        except Exception:
                            continue
            else:
                # skipped entry (dict with keys test_name, status, reason)
                skipped_entry = {
                    "test_name": r.get("test_name"),
                    "status": "skipped",
                    "reason": r.get("reason"),
                    "fdr_rejected": False,
                    "fdr_q": q,
                }
                serialized_results.append(skipped_entry)
 
        # Scorecard
        failed_count = sum(1 for r in serialized_results if r.get('fdr_rejected'))
        mean_effect = statistics.mean(all_effects) if all_effects else None
        p_stats = self._pvalue_stats(p_values)
        scorecard = {
            "failed_tests": failed_count,
            "mean_effect_size": mean_effect,
            "p_value_distribution": p_stats,
            "total_tests": len(serialized_results),
            "fdr_q": q,
        }
 
        # Observability / meta information for reports
        meta: Dict[str, Any] = {}
        try:
            meta["python"] = platform.python_version()
            meta["python_full"] = sys.version
            meta["platform"] = platform.platform()
        except Exception:
            meta["python"] = None
            meta["python_full"] = None
            meta["platform"] = None
 
        # Try to capture optional scientific stack versions
        try:
            import numpy as _np  # type: ignore
            meta["numpy"] = getattr(_np, "__version__", None)
        except Exception:
            meta["numpy"] = None
        try:
            import scipy as _sp  # type: ignore
            meta["scipy"] = getattr(_sp, "__version__", None)
        except Exception:
            meta["scipy"] = None
 
        # Plugins information: include class/module and best-effort package version
        def _pkg_version_for(module_name: str):
            root = (module_name.split(".") or [None])[0]
            if not root:
                return None
            try:
                return importlib.metadata.version(root)
            except Exception:
                return None
 
        plugins_info: Dict[str, List[Dict[str, Any]]] = {"transforms": [], "tests": [], "visuals": []}
        for name, plug in self._transforms.items():
            plugins_info["transforms"].append(
                {
                    "name": name,
                    "class": plug.__class__.__name__,
                    "module": plug.__class__.__module__,
                    "package_version": _pkg_version_for(plug.__class__.__module__),
                }
            )
        for name, plug in self._tests.items():
            plugins_info["tests"].append(
                {
                    "name": name,
                    "class": plug.__class__.__name__,
                    "module": plug.__class__.__module__,
                    "package_version": _pkg_version_for(plug.__class__.__module__),
                }
            )
        for name, plug in self._visuals.items():
            plugins_info["visuals"].append(
                {
                    "name": name,
                    "class": plug.__class__.__name__,
                    "module": plug.__class__.__module__,
                    "package_version": _pkg_version_for(plug.__class__.__module__),
                }
            )
        meta["plugins"] = plugins_info
 
        # Config & input hashes for reproducibility
        try:
            cfg_json = json.dumps(config, sort_keys=True, default=str)
            meta["config_hash"] = hashlib.sha256(cfg_json.encode("utf-8")).hexdigest()
        except Exception:
            meta["config_hash"] = None
        try:
            meta["input_hash"] = hashlib.sha256(input_bytes).hexdigest()
        except Exception:
            meta["input_hash"] = None
 
        output = {"results": serialized_results, "scorecard": scorecard, "meta": meta}
 
        # Optional: generate a minimal HTML report if requested via config['html_report']
        html_path = config.get("html_report")
        if html_path:
            try:
                import json as _json
                import html as _html
 
                parts = []
                parts.append('<!doctype html>')
                parts.append('<html><head><meta charset="utf-8"><title>PatternLab Report</title></head><body>')
                parts.append('<h1>PatternLab Report</h1>')
 
                # Meta section
                parts.append('<h2>Meta</h2>')
                parts.append('<table border="1" cellpadding="4">')
                for k, v in meta.items():
                    parts.append(f'<tr><th style="text-align:left">{_html.escape(str(k))}</th><td>{_html.escape(_json.dumps(v))}</td></tr>')
                parts.append('</table>')
 
                # Summary table
                parts.append('<h2>Summary</h2>')
                parts.append('<table border="1" cellpadding="4">')
                for k, v in scorecard.items():
                    parts.append(f'<tr><th style="text-align:left">{_html.escape(str(k))}</th><td>{_html.escape(_json.dumps(v))}</td></tr>')
                parts.append('</table>')
 
                # Results list
                parts.append('<h2>Results</h2>')
                for res in serialized_results:
                    parts.append(f'<div class="result"><h3>{_html.escape(str(res.get("test_name", "")))}</h3>')
                    parts.append(f'<p>Status: {_html.escape(str(res.get("status")))}')
                    if res.get("fdr_rejected"):
                        parts.append(' <strong style="color:red">[FDR rejected]</strong>')
                    parts.append('</p>')
 
                    if isinstance(res.get("metrics"), dict) and res.get("metrics"):
                        parts.append('<details><summary>Metrics</summary><pre>')
                        parts.append(_html.escape(_json.dumps(res.get("metrics"), indent=2)))
                        parts.append('</pre></details>')
 
                    if isinstance(res.get("visuals"), dict):
                        for vname, v in res.get("visuals", {}).items():
                            parts.append(f'<h4>{_html.escape(vname)}</h4>')
                            mime = v.get("mime", "image/svg+xml")
                            if "data_base64" in v:
                                # embed as data URI
                                parts.append(f'<img alt="{_html.escape(vname)}" src="data:{_html.escape(mime)};base64,{v["data_base64"]}" style="max-width:100%;height:auto"/>')
                            elif "path" in v:
                                parts.append(f'<img alt="{_html.escape(vname)}" src="{_html.escape(v["path"])}" style="max-width:100%;height:auto"/>')
                    parts.append('</div><hr/>')
 
                parts.append('</body></html>')
                html_text = "\n".join(parts)
 
                # Ensure directory exists
                dirn = os.path.dirname(html_path) or "."
                os.makedirs(dirn, exist_ok=True)
                with open(html_path, "w", encoding="utf-8") as hf:
                    hf.write(html_text)
            except Exception:
                # Never fail the analysis because HTML export failed; swallow errors.
                pass
 
        return output
 
    def get_available_transforms(self) -> List[str]:
        """Get list of available transform names."""
        return list(self._transforms.keys())

    def get_available_tests(self) -> List[str]:
        """Get list of available test names."""
        return list(self._tests.keys())

    def get_available_visuals(self) -> List[str]:
        """Get list of available visual plugin names."""
        return list(self._visuals.keys())
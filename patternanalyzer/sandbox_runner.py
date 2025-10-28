"""Subprocess runner for sandboxed plugin execution.

Reads a JSON payload from stdin with keys:
  - module: module name containing the plugin class
  - class: class name of the plugin
  - test_name: test name (for error messages)
  - data_b64: base64-encoded input bytes (or null)
  - params: params dict for plugin.run/safe_run
  - mem_mb: optional memory limit in megabytes (best-effort; Unix-only)

Writes a single JSON object to stdout describing either a serialized TestResult-like
dict or an error dict: {"status":"error","reason": "..."}.
"""
import sys
import json
import base64
import time
import traceback
import os


def main():
    try:
        raw = sys.stdin.read()
        if not raw:
            print(json.dumps({"status": "error", "reason": "no_input"}))
            return
        payload = json.loads(raw)
        module = payload.get("module")
        cls_name = payload.get("class")
        test_name = payload.get("test_name")
        data_b64 = payload.get("data_b64")
        params = payload.get("params", {}) or {}
        mem_mb = payload.get("mem_mb")

        data_bytes = None
        if data_b64 is not None:
            try:
                data_bytes = base64.b64decode(data_b64)
            except Exception as e:
                print(json.dumps({"status": "error", "reason": f"invalid_base64:{e}"}))
                return

        # Apply memory limits on Unix-like systems if requested (best-effort).
        if mem_mb and os.name != "nt":
            try:
                import resource  # type: ignore
                bytes_limit = int(mem_mb) * 1024 * 1024
                # Limit address space (RLIMIT_AS) so allocations above this will fail.
                resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
            except Exception:
                # Do not fail startup just because we couldn't set limits.
                pass

        # Import plugin class
        try:
            mod = __import__(module, fromlist=["*"])
            klass = getattr(mod, cls_name)
            inst = klass()
        except Exception as e:
            print(json.dumps({"status": "error", "reason": f"import_error:{e}"}))
            return

        try:
            # Import plugin API helpers for result serialization
            from patternanalyzer.plugin_api import BytesView, TestResult, serialize_testresult  # type: ignore

            bv = BytesView(data_bytes) if data_bytes is not None else None
            start = time.perf_counter()
            # Prefer safe_run if available
            if hasattr(inst, "safe_run"):
                res = inst.safe_run(bv, params)
            else:
                res = inst.run(bv, params)
            end = time.perf_counter()
            duration_ms = (end - start) * 1000.0

            if isinstance(res, TestResult):
                try:
                    if getattr(res, "time_ms", None) is None:
                        res.time_ms = duration_ms
                except Exception:
                    pass
                try:
                    if getattr(res, "bytes_processed", None) is None and bv is not None:
                        try:
                            res.bytes_processed = len(bv.to_bytes())
                        except Exception:
                            res.bytes_processed = None
                except Exception:
                    pass
                out = serialize_testresult(res)
                out["status"] = "completed"
                out["time_ms"] = getattr(res, "time_ms", None)
                out["bytes_processed"] = getattr(res, "bytes_processed", None)
                print(json.dumps(out, default=str))
                return
            else:
                # Plugin returned a dict (likely an error dict from safe_run) or other serializable object
                try:
                    print(json.dumps(res, default=str))
                except Exception:
                    # Fallback: stringify
                    print(json.dumps({"status": "error", "reason": "non_serializable_result"}))
                return

        except Exception as e:
            tb = traceback.format_exc()
            print(json.dumps({"status": "error", "reason": str(e), "exc": tb}))
            return

    except Exception as e:
        tb = traceback.format_exc()
        print(json.dumps({"status": "error", "reason": str(e), "exc": tb}))
        return


if __name__ == "__main__":
    main()
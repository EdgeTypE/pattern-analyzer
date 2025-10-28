"""patternanalyzer.tui — Simple Textual TUI application."""

from typing import Optional
from textual.app import App, ComposeResult
# ScrollView API moved between textual versions; try importing from widgets first,
# then from containers, otherwise provide a minimal fallback shim so the TUI still runs.
try:
    from textual.widgets import Header, Footer, Static, DirectoryTree, Checkbox, Button, LoadingIndicator, DataTable
    from textual.containers import VerticalScroll as ScrollView
    _SCROLL_SRC = 'textual.containers'
except Exception:
    try:
        # some textual versions expose ScrollView from widgets
        from textual.widgets import Header, Footer, Static, DirectoryTree, Checkbox, Button, LoadingIndicator, DataTable, ScrollView
        _SCROLL_SRC = 'textual.widgets'
    except Exception:
        # final fallback: emulate a simple ScrollView using Container so imports succeed and children are rendered
        from textual.widgets import Header, Footer, Static, DirectoryTree, Checkbox, Button, LoadingIndicator, DataTable
        from textual.containers import Container
        class ScrollView(Container):  # type: ignore
            """Fallback ScrollView used when textual does not provide one."""
            pass
        _SCROLL_SRC = 'fallback'
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from patternanalyzer.engine import Engine
import json

class PatternAnalyzerTUI(App):
    """Simple application based on Textual.app.

    This interface only provides the required widgets:
    - DirectoryTree for file selection
    - Checkboxes for selecting tests to run (engine.get_available_tests())
    - Start and Exit buttons
    - DataTable for analysis results and clickable results list (modal for metric display)
    """

    CSS = """
    #body { height: 1fr; }
    #left { width: 50%; min-width: 30; }
    #right { width: 50%; padding: 1 1; }
    #tests_scroll { height: 1fr; border: round $accent; padding: 1; }
    #controls { padding-top: 1; }
    #loading { padding-left: 1; }
    #scorecard { border: round $accent; padding: 1; height: auto; max-height: 10; overflow: auto; }
    #results_table { height: 1fr; border: round $accent; padding: 1; }
    #results_scroll { height: 10; border: round $accent; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        """Compose the components."""
        yield Header()
        with Container(id="body"):
            with Horizontal():
                # Left: file tree / selector
                yield Vertical(
                    Static("File Selection", id="file_label"),
                    DirectoryTree(".", id="file_tree"),
                    id="left",
                )
                # Right: test list, results, and control buttons
                yield Vertical(
                    Static("Available Tests (Select with Checkboxes)", id="tests_label"),
                    ScrollView(id="tests_scroll"),
                    Static("Scorecard", id="score_label"),
                    Static("", id="scorecard", expand=False),
                    Static("Results (Table)", id="results_label"),
                    DataTable(id="results_table"),
                    Static("Clickable Results List", id="results_list_label"),
                    ScrollView(id="results_scroll"),
                    Static("", id="status", expand=False),  # For status messages
                    Horizontal(
                        Button("Start", id="start_btn", variant="success"),
                        Button("Exit", id="exit_btn", variant="error"),
                        id="controls",
                    ),
                    id="right",
                )
        yield Footer()

    def on_mount(self) -> None:
        """Load test checkboxes after the app is mounted."""
        # Analysis not running initially
        self._analysis_running = False
        # Mapping for clickable result buttons -> metrics
        self._result_metrics = {}

        # Engine instance used only to get test names; no execution will be performed.
        try:
            eng = Engine()
            tests = eng.get_available_tests()
        except Exception:
            tests = []

        tests_scroll: Optional[ScrollView] = self.query_one("#tests_scroll", ScrollView)
        # Dynamically add Checkboxes
        for i, tname in enumerate(tests):
            cb = Checkbox(tname, id=f"test_{i}")
            tests_scroll.mount(cb)

        # Prepare DataTable columns (for discovery, to avoid recreation)
        try:
            table = self.query_one("#results_table", DataTable)
            # clear any existing columns/rows
            try:
                table.clear()
            except Exception:
                pass
            try:
                table.add_column("test_name")
                table.add_column("status")
                table.add_column("p_value")
                table.add_column("fdr_rejected")
            except Exception:
                pass
        except Exception:
            pass

    def _format_scorecard(self, scorecard: dict) -> str:
        """Format the scorecard as formatted text."""
        try:
            lines = []
            lines.append(f"Failed tests: {scorecard.get('failed_tests')}")
            lines.append(f"Mean effect size: {scorecard.get('mean_effect_size')}")
            pvd = scorecard.get("p_value_distribution", {})
            lines.append(f"P-value distribution: count={pvd.get('count')}, mean={pvd.get('mean')}, median={pvd.get('median')}, stdev={pvd.get('stdev')}")
            if isinstance(pvd.get("histogram"), dict):
                lines.append("Histogram:")
                for k, v in pvd.get("histogram").items():
                    lines.append(f"  {k}: {v}")
            lines.append(f"Total tests: {scorecard.get('total_tests')}")
            lines.append(f"FDR q: {scorecard.get('fdr_q')}")
            return "\n".join(lines)
        except Exception:
            return json.dumps(scorecard, indent=2, ensure_ascii=False)

    def _display_results(self, output: dict) -> None:
        """Display Engine.analyze output in the UI: scorecard and results list."""
        try:
            scorecard = output.get("scorecard", {}) if isinstance(output, dict) else {}
            results = output.get("results", []) if isinstance(output, dict) else []
        except Exception:
            scorecard = {}
            results = []

        # Update scorecard Static
        try:
            sc = self.query_one("#scorecard", Static)
            sc.update(self._format_scorecard(scorecard))
        except Exception:
            pass

        # Populate DataTable summary
        try:
            table = self.query_one("#results_table", DataTable)
            try:
                table.clear()
            except Exception:
                pass
            # ensure columns exist
            try:
                if not table.columns:
                    table.add_column("test_name")
                    table.add_column("status")
                    table.add_column("p_value")
                    table.add_column("fdr_rejected")
            except Exception:
                pass
            # Add rows and record metrics mapping for clickable list
            self._result_metrics = {}
            for i, r in enumerate(results):
                tname = r.get("test_name") or str(r.get("name") or f"result_{i}")
                status = r.get("status")
                p_val = r.get("p_value")
                fdr = r.get("fdr_rejected", False)
                try:
                    table.add_row(str(tname), str(status), str(p_val), str(fdr), key=str(i))
                except Exception:
                    try:
                        # fallback to add_row without key
                        table.add_row(str(tname), str(status), str(p_val), str(fdr))
                    except Exception:
                        pass
                # Prepare metrics payload for modal display
                metrics = {
                    "p_value": p_val,
                    "fdr_rejected": fdr,
                    "status": status,
                    "effect_sizes": r.get("effect_sizes"),
                    "metrics": r.get("metrics"),
                    "flags": r.get("flags"),
                    "time_ms": r.get("time_ms"),
                    "bytes_processed": r.get("bytes_processed"),
                }
                self._result_metrics[f"res_btn_{i}"] = {"test_name": tname, "metrics": metrics}
        except Exception:
            pass

        # Populate clickable results list (Buttons inside ScrollView)
        try:
            rs = self.query_one("#results_scroll", ScrollView)
            # clear existing children (best-effort)
            try:
                for child in list(rs.children):
                    child.remove()
            except Exception:
                pass
            for i, r in enumerate(results):
                tname = r.get("test_name") or str(r.get("name") or f"result_{i}")
                btn = Button(str(tname), id=f"res_btn_{i}")
                rs.mount(btn)
        except Exception:
            pass

    def _show_loading(self) -> None:
        """Show LoadingIndicator in the right panel."""
        # If already shown, do not remount
        if self.query("#loading"):
            return
        try:
            right = self.query_one("#right", Vertical)
            right.mount(LoadingIndicator(id="loading"))
        except Exception:
            pass

    def _hide_loading(self) -> None:
        """Remove the LoadingIndicator."""
        try:
            loading = self.query_one("#loading")
            loading.remove()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Triggered when buttons are pressed: Start, Exit, result buttons, and modal close."""
        btn_id = getattr(event.button, "id", None)
        if btn_id == "exit_btn":
            self.exit()
            return

        if btn_id == "start_btn":
            # Collect selected tests and selected file path
            selected_tests = [cb.label for cb in self.query(Checkbox) if getattr(cb, "id", "").startswith("test_") and cb.value]
            file_tree = self.query_one(DirectoryTree)
            # Safely read selected file info from DirectoryTree
            file_path = None
            for attr in ("path", "cursor_path", "selected_path", "cursor", "selected_node"):
                val = getattr(file_tree, attr, None)
                if val:
                    # selected_node may exist; use path attribute if available
                    if hasattr(val, "path"):
                        file_path = getattr(val, "path")
                    else:
                        file_path = str(val)
                    break

            status = self.query_one("#status", Static)

            # If analysis is already running, do not start a new one
            if getattr(self, "_analysis_running", False):
                status.update("Analysis is already running")
                return

            # Preparation: Show loading, set flag
            self._analysis_running = True
            self._show_loading()
            status.update(f"Analysis started — selected tests: {len(selected_tests)}")

            # Worker function: Calls Engine.analyze in the background
            def _worker():
                try:
                    eng = Engine()
                    data = b""
                    if file_path:
                        try:
                            with open(file_path, "rb") as f:
                                data = f.read()
                        except Exception:
                            data = b""
                    config = {"tests": [{"name": t, "params": {}} for t in selected_tests]}
                    # Engine's heavy work is done here
                    return eng.analyze(data, config)
                except Exception as e:
                    return {"error": str(e)}

            # Callback to be called when done
            def _on_done(result):
                self._analysis_running = False
                self._hide_loading()
                try:
                    if isinstance(result, dict) and "error" in result:
                        status.update(f"Analysis error: {result['error']}")
                    else:
                        status.update("Analysis completed — results displayed")
                        self._display_results(result or {})
                except Exception as e:
                    status.update(f"Display error: {e}")

            # Run in background with standard threading
            try:
                import threading
                def _thread_worker():
                    result = _worker()
                    # Run callback in main thread
                    self.call_from_thread(_on_done, result)
                thread = threading.Thread(target=_thread_worker, daemon=True)
                thread.start()
            except Exception as e:
                # Clean up in case of error
                self._analysis_running = False
                self._hide_loading()
                status.update(f"Analysis could not start: {e}")
            return

        # Modal close button
        if btn_id == "modal_close":
            try:
                self.pop_screen()
            except Exception:
                pass
            return

        # Clicking on result list buttons: show metrics in modal
        if isinstance(btn_id, str) and btn_id.startswith("res_btn_"):
            info = self._result_metrics.get(btn_id)
            if not info:
                return
            test_name = info.get("test_name", "metrics")
            metrics = info.get("metrics", {}) or {}
            try:
                metrics_text = json.dumps(metrics, indent=2, ensure_ascii=False)
            except Exception:
                metrics_text = str(metrics)
            try:
                # Push a modal screen with metrics
                self.push_screen(MetricsModal(test_name, metrics_text))
            except Exception:
                pass

    # Additional event handlers or helpers can be added here if needed.

class MetricsModal(ModalScreen):
    """Simple modal screen: displays metrics for the selected test."""
    def __init__(self, test_name: str, metrics_text: str) -> None:
        super().__init__()
        self.test_name = test_name
        self.metrics_text = metrics_text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"Metrics — {self.test_name}", id="modal_title"),
            (
                Static(self.metrics_text, id="modal_metrics")
                if _SCROLL_SRC == 'fallback'
                else
                ScrollView(self.metrics_text, id="modal_metrics")
                if _SCROLL_SRC == 'textual.widgets'
                else
                ScrollView(Static(self.metrics_text), id="modal_metrics")
            ),
            Horizontal(
                Button("Close", id="modal_close", variant="primary"),
            ),
        )

if __name__ == "__main__":
    PatternAnalyzerTUI().run()
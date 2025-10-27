"""patternlab.tui — Basit Textual TUI uygulaması."""
 
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
from patternlab.engine import Engine
import json

class PatternLabTUI(App):
    """Textual.app tabanlı basit uygulama.
 
    Bu arayüz sadece istenen widget'ları sağlar:
    - Dosya seçimi için DirectoryTree
    - Çalıştırılacak testleri seçmek için Checkbox'lar (engine.get_available_tests())
    - Başlat ve Çıkış için Button'lar
    - Analiz sonuçları için DataTable ve tıklanabilir sonuç listesi (modal ile metrik gösterimi)
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
        """Bileşenleri oluştur."""
        yield Header()
        with Container(id="body"):
            with Horizontal():
                # Sol: dosya ağacı / seçici
                yield Vertical(
                    Static("Dosya seçimi", id="file_label"),
                    DirectoryTree(".", id="file_tree"),
                    id="left",
                )
                # Sağ: test listesi, sonuçlar ve kontrol düğmeleri
                yield Vertical(
                    Static("Mevcut Testler (Checkbox ile seçin)", id="tests_label"),
                    ScrollView(id="tests_scroll"),
                    Static("Scorecard", id="score_label"),
                    Static("", id="scorecard", expand=False),
                    Static("Sonuçlar (tablo)", id="results_label"),
                    DataTable(id="results_table"),
                    Static("Tıklanabilir sonuç listesi", id="results_list_label"),
                    ScrollView(id="results_scroll"),
                    Static("", id="status", expand=False),  # Status mesajları için
                    Horizontal(
                        Button("Başlat", id="start_btn", variant="success"),
                        Button("Çıkış", id="exit_btn", variant="error"),
                        id="controls",
                    ),
                    id="right",
                )
        yield Footer()
 
    def on_mount(self) -> None:
        """Uygulama mount edildikten sonra test checkbox'larını yükle."""
        # Başlangıçta analiz çalışmıyor
        self._analysis_running = False
        # Mapping for clickable result buttons -> metrics
        self._result_metrics = {}
 
        # Motor örneği sadece test isimlerini almak için kullanılır; çalıştırma yapılmayacak.
        try:
            eng = Engine()
            tests = eng.get_available_tests()
        except Exception:
            tests = []
 
        tests_scroll: Optional[ScrollView] = self.query_one("#tests_scroll", ScrollView)
        # Dynamic olarak Checkbox'ları ekle
        for i, tname in enumerate(tests):
            cb = Checkbox(tname, id=f"test_{i}")
            tests_scroll.mount(cb)
 
        # Prepare DataTable columns (keşif amaçlı, tekrar oluşturmayı önlemek için)
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
        """Scorecard'ı biçimlendirilmiş metin olarak döndür."""
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
        """Engine.analyze çıktısını UI içinde göster: scorecard ve sonuç listesi."""
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
        """LoadingIndicator'ı sağ panelde göster."""
        # Eğer zaten gösteriliyorsa yeniden mount etme
        if self.query("#loading"):
            return
        try:
            right = self.query_one("#right", Vertical)
            right.mount(LoadingIndicator(id="loading"))
        except Exception:
            pass
 
    def _hide_loading(self) -> None:
        """LoadingIndicator'ı kaldır."""
        try:
            loading = self.query_one("#loading")
            loading.remove()
        except Exception:
            pass
 
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Butonlara basılınca çalışır: Başlat, Çıkış, sonuç butonları ve modal kapatma."""
        btn_id = getattr(event.button, "id", None)
        if btn_id == "exit_btn":
            self.exit()
            return
 
        if btn_id == "start_btn":
            # Seçili testleri ve seçili dosya yolunu topla
            selected_tests = [cb.label for cb in self.query(Checkbox) if getattr(cb, "id", "").startswith("test_") and cb.value]
            file_tree = self.query_one(DirectoryTree)
            # DirectoryTree içindeki seçili dosya bilgisini güvenli okumaya çalış
            file_path = None
            for attr in ("path", "cursor_path", "selected_path", "cursor", "selected_node"):
                val = getattr(file_tree, attr, None)
                if val:
                    # selected_node olabilir; path özniteliği varsa kullan
                    if hasattr(val, "path"):
                        file_path = getattr(val, "path")
                    else:
                        file_path = str(val)
                    break
 
            status = self.query_one("#status", Static)
  
            # Eğer analiz zaten çalışıyorsa yeni analiz başlatma
            if getattr(self, "_analysis_running", False):
                status.update("Analiz zaten çalışıyor")
                return
  
            # Hazırlık: Loading göster, flag set
            self._analysis_running = True
            self._show_loading()
            status.update(f"Analiz başlatıldı — seçili testler: {len(selected_tests)}")
 
            # Worker fonksiyonu: Engine.analyze'ı arka planda çağırır
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
                    # Motorun ağır işi burada yapılır
                    return eng.analyze(data, config)
                except Exception as e:
                    return {"error": str(e)}
 
            # tamamlandığında çağrılacak callback
            def _on_done(result):
                self._analysis_running = False
                self._hide_loading()
                try:
                    if isinstance(result, dict) and "error" in result:
                        status.update(f"Analiz hatası: {result['error']}")
                    else:
                        status.update("Analiz tamamlandı — sonuçlar gösteriliyor")
                        self._display_results(result or {})
                except Exception as e:
                    status.update(f"Görüntüleme hatası: {e}")
 
            # Standart threading ile arka plan çalıştır
            try:
                import threading
                def _thread_worker():
                    result = _worker()
                    # Callback'i main thread'de çalıştır
                    self.call_from_thread(_on_done, result)
                thread = threading.Thread(target=_thread_worker, daemon=True)
                thread.start()
            except Exception as e:
                # Hata durumunda temizle
                self._analysis_running = False
                self._hide_loading()
                status.update(f"Analiz başlatılamadı: {e}")
            return
 
        # Modal kapatma düğmesi
        if btn_id == "modal_close":
            try:
                self.pop_screen()
            except Exception:
                pass
            return
 
        # Sonuç listesi butonlarına tıklama: modal içinde metrikleri göster
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
 
    # Ek event handlerler veya yardımcılar gerektiğinde buraya eklenebilir.
 
class MetricsModal(ModalScreen):
    """Basit modal ekran: seçili testin metriklerini gösterir."""
    def __init__(self, test_name: str, metrics_text: str) -> None:
        super().__init__()
        self.test_name = test_name
        self.metrics_text = metrics_text
 
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"Metrikler — {self.test_name}", id="modal_title"),
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
                Button("Kapat", id="modal_close", variant="primary"),
            ),
        )
 
if __name__ == "__main__":
    PatternLabTUI().run()
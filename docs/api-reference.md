# API Reference

Bu sayfa PatternLab paketinin programatik API'sinin kısa bir özetini sağlar. Daha geniş referans için kaynak koduna bakın: [`patternlab/engine.py`](patternlab/engine.py:1), [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1), [`patternlab/cli.py`](patternlab/cli.py:1).

Önemli sınıflar ve fonksiyonlar
- Engine
  - Ana analiz akışını yöneten sınıf. Kullanım: `Engine().analyze(data_bytes, config)`.
  - Kaydetme: `engine.register_test(name, plugin_instance)` ve `engine.register_transform(...)`.
  - Kaynak: [`patternlab/engine.py`](patternlab/engine.py:1)
- TestPlugin, TransformPlugin, VisualPlugin
  - Eklenti taban sınıfları. Yeni eklenti yazarken genişletin.
  - Ayrıntılar: [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1)
- BytesView
  - Veri görünümü yardımcı sınıfı (bit_view, slice, vb.).
  - Kullanım: test eklentileri run metodunda `data: BytesView`.
- TestResult
  - Test sonucu taşıyıcısı. Alanlar: test_name, passed, p_value, metrics, z_score, p_values, effect_sizes, flags, fdr_rejected, fdr_q.
  - Serialize: `serialize_testresult(result)` (bakınız `patternlab/plugin_api.py`).

Hızlı Örnek — Python
```python
from patternlab.engine import Engine
from patternlab.plugins.monobit import MonobitTest

engine = Engine()
engine.register_test("monobit", MonobitTest())

with open("test.bin","rb") as f:
    data = f.read()

config = {"tests":[{"name":"monobit","params":{"alpha":0.01}}]}
output = engine.analyze(data, config)
print(output["scorecard"])
```

CLI ile entegrasyon
- CLI entrypoint: [`patternlab/cli.py`](patternlab/cli.py:1)
- Örnek: `patternlab analyze input.bin -c docs/configs/example.yml -o report.json`

Dokümantasyon otomatik türetme
- Eğer ayrıntılı API referansı istenirse, `mkdocstrings` + `pytkdocs` ile otomatik döküm oluşturulabilir. Bunun için `mkdocs.yml` içinde `mkdocstrings` eklentisi ve `requirements-docs.txt` eklenmesi gerekir.

Kaynak dosyaları
- Engine: [`patternlab/engine.py`](patternlab/engine.py:1)
- Plugin API: [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1)
- CLI: [`patternlab/cli.py`](patternlab/cli.py:1)
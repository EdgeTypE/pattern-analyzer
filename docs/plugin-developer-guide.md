# Plugin Geliştirici Kılavuzu

Bu doküman PatternLab için eklenti (plugin) geliştirme adımlarını açıklar: test, dönüştürme (transform) ve görselleştirme (visual) eklentileri.

Temel noktalar:
- Eklentiler üç türdedir: TestPlugin, TransformPlugin, VisualPlugin.
- Temel API tanımları: [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1)

Gereksinimler
- Python 3.8+
- Proje kurulumu için dev ortamı; paket bağımlılıkları optional (numpy, scipy, pyyaml)

1) Yeni Bir Test Plugin'i Yazma
- Test eklentileri TestPlugin sınıfını genişletir. Aşağıda minimal bir örnek:

```python
from patternlab.plugin_api import TestPlugin, BytesView, TestResult

class MyTest(TestPlugin):
    """Açıklama: Basit örnek test."""

    requires = ['bits']

    def describe(self) -> str:
        return "my_simple_test"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        ones = sum(bits)
        n = len(bits)
        # basit karar
        passed = (ones / n) > float(params.get('threshold', 0.5)) if n else True
        return TestResult(test_name="my_simple_test", passed=passed, p_value=None, metrics={"ones": ones, "n": n})
```

Açıklamalar:
- `requires` listesi engine tarafından testin çalıştırılabilmesi için gereken veri görünümünü belirtir.
- `run` TestResult döndürmelidir; TestResult yapısı için bakınız [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1).

2) Eklentiyi projeye ekleme
- Yeni dosyayı `patternlab/plugins/` dizinine koyun; örneğin [`patternlab/plugins/my_test.py`](patternlab/plugins/my_test.py:1).
- Engine otomatik olarak yerleşik eklentileri kaydeder; yeni eklentileri elle kaydetmek için [`patternlab/engine.py`](patternlab/engine.py:1) içindeki `register_test` kullanılabilir.

3) Config ile yapılandırma
- CLI ve programatik çağrılar için config sözlüğü veya dosyası kullanılır. Örnek yapı:

```json
{
  "transforms": [{"name": "xor_const", "params": {"xor_value": 55}}],
  "tests": [{"name": "my_simple_test", "params": {"threshold": 0.6}}],
  "fdr_q": 0.05
}
```

Bu yapı hakkında detaylar için [`patternlab/cli.py`](patternlab/cli.py:1)'de konfigürasyon normalizasyonuna bakın.

4) Testleri çalıştırma
- CLI ile:

```bash
# JSON config kullanarak
patternlab analyze ./test.bin -c ./configs/example.json -o report.json
```

- Programatik olarak:

```python
from patternlab.engine import Engine
engine = Engine()
with open("test.bin", "rb") as f:
    data = f.read()
output = engine.analyze(data, {
    "tests": [{"name": "my_simple_test", "params": {"threshold": 0.6}}]
})
print(output)
```

5) Görsel eklenti (VisualPlugin) kullanma
- VisualPlugin.render(result, params) bytes döndürmelidir (ör. SVG/PNG).
- Engine sonuçlara görselleri base64 olarak ekler; görsel eklentileri `patternlab/plugins/` içine yerleştirin.

6) Hata yönetimi ve güvenlik
- TestPlugin.safe_run() wrapper'ı engine tarafından kullanılır; eklentiniz exception fırlatırsa engine bunu hata olarak kaydeder.
- Eklenti kodunuzda dışarıdan gelen parametrelere karşı validation uygulayın.

7) Unit test yazma
- Mevcut testlere bakın: [`tests/test_monobit.py`](tests/test_monobit.py:1) örnek testlerden biridir.
- Pytest ile yeni eklentinizi test edin; BytesView ve TestResult yardımcıları kullanılabilir.

8) Yayınlama (Opsiyonel)
- Paket içi entry point tanımları kullanılarak eklenti yayınlanabilir (grup: 'patternlab.plugins').
- `importlib.metadata.entry_points` ile yüklenen entry point sınıfları otomatik register edilir. Daha fazla için [`patternlab/engine.py`](patternlab/engine.py:1) dosyasına bakın.

Ek referans
- API: [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1)
- Engine: [`patternlab/engine.py`](patternlab/engine.py:1)
- CLI: [`patternlab/cli.py`](patternlab/cli.py:1)

Bu kılavuz, hızlı bir başlangıç sağlar. İleri seviye konu veya örnek isterseniz ayrı bir doküman eklenebilir.
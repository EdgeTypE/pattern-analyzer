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

## Yeni Test Eklentileri: frequency_within_block, maurers_universal, linear_complexity

Aşağıda proje içinde eklenmiş/ güncellenmiş üç test eklentisi için geliştirici notları bulunmaktadır. Her bölümde eklentinin amacı (NIST ile bağlantı), kabul edilen parametreler/varsayılanlar, döndürülen önemli metrikler ve kısa kullanım örneği yer alır.

### Frequency Test within a Block
- Dosya: [`patternlab/plugins/frequency_within_block.py`](patternlab/plugins/frequency_within_block.py:1)  
- Amaç ve NIST bağlantısı: NIST SP 800‑22 içindeki "Frequency Test within a Block" yaklaşımına dayanır. Girdi bit dizisini M boyutlu bloklara ayırır ve her bloktaki 1 oranlarının beklenen 0.5 değerinden sapmasını chi-square benzeri bir istatistik ile değerlendirir.
- Parametreler ve varsayılanlar:
  - `block_size` (int): açıkça verilirse kullanılır (M).
  - `default_block_size` (int, default 128): `block_size` verilmediğinde kullanılacak varsayılan.
  - `alpha` (float, default 0.01): anlamlılık seviyesi.
  - Seçme heuristiği: Eğer toplam bit sayısı n 100 ile tam bölünürse M = n // 100 seçilebilir.
- Çıktı metrikleri (TestResult.metrics):
  - `block_count`, `block_size`, `total_bits`
  - `ones_counts`: blok başına 1 sayıları
  - `proportions`: blok başına 1 oranları
  - `chi_square`
- Kullanım örneği:
```python
# python
from patternlab.plugins.frequency_within_block import FrequencyWithinBlockTest
from patternlab.plugin_api import BytesView

plugin = FrequencyWithinBlockTest()
data = BytesView(b'\xff\x00\xaa')  # örnek
result = plugin.run(data, {"block_size": 8, "alpha": 0.01})
print(result.p_value, result.metrics["chi_square"])
```

### Maurer's Universal Test (güncellenmiş)
- Dosya: [`patternlab/plugins/maurers_universal.py`](patternlab/plugins/maurers_universal.py:1)  
- Amaç ve NIST bağlantısı: NIST SP 800‑22'de tanımlanan Maurer’s Universal Statistical Test'e uyumlu bir uygulamadır. Desenlerin tekrar uzaklıklarının log2 ortalaması üzerinden dizinin beklenen sıkılık/karmaşıklığını ölçer.
- Parametreler ve varsayılanlar:
  - `L` (int, default 6): blok uzunluğu (NIST önerisi 6..16 arası).
  - `Q` (int, default 10 * 2**L): başlatma (init) blok sayısı.
  - `min_blocks` (int): toplam blok sayısı için minimum gereksinim; varsayılan Q + 1000 (NIST gereksinimine uyum).
  - `alpha` (float, default 0.01)
- Önemli davranışlar:
  - Yetersiz blok sayısında test "skipped" (atlandı) olarak döner ve sebebi açıkça belirtilir.
  - NIST referans ortalama ve varyans tablosu (L=6..16) kullanılır.
- Çıktı metrikleri:
  - `L`, `blocks` (toplam blok), `init_Q`, `processed_blocks` (K), `fn` (ortalama log2 mesafe), `expected`, `variance`, `z_score`, `total_bits`
- Kullanım örneği:
```python
# python
from patternlab.plugins.maurers_universal import MaurersUniversalTest
from patternlab.plugin_api import BytesView

plugin = MaurersUniversalTest()
data = BytesView(open("test.bin","rb").read())
res = plugin.run(data, {"L": 6})
if isinstance(res, dict) and res.get("status") == "skipped":
    print("Skipped:", res["reason"])
else:
    print(res.p_value, res.metrics["fn"])
```

### Linear Complexity (güncellenmiş)
- Dosya: [`patternlab/plugins/linear_complexity.py`](patternlab/plugins/linear_complexity.py:1)  
- Amaç ve NIST bağlantısı: Berlekamp–Massey algoritması ile bit dizisinin GF(2) üzerindeki lineer kompleksitesini hesaplar. NIST SP 800‑22'deki lineer kompleksite testine benzer istatistikler ve yaklaşık p-değerleri sunar; proje içinde diagnostic amaçlı kullanılabilir.
- Parametreler ve varsayılanlar:
  - `alpha` (float, default 0.01)
  - Girdi uzunluğu n==0 ise test hata/uyarı içeren bir TestResult döndürür.
- Hesaplama ve çıktı:
  - `linear_complexity` (L), `n` (bit uzunluğu)
  - Ayrıca NIST‑tarzı yaklaşık `mu`, `sigma`, `T`, `z`, `p_value_backend` (hangi yöntemin kullanıldığı)
  - P-değeri için SciPy varsa `scipy.stats.norm` kullanılır, yoksa `math.erfc` fallback.
- Kullanım örneği:
```python
# python
from patternlab.plugins.linear_complexity import LinearComplexityTest
from patternlab.plugin_api import BytesView

plugin = LinearComplexityTest()
res = plugin.run(BytesView(b'\xff\x00\x0f'), {})
print(res.metrics["linear_complexity"], res.p_value)
```

Bu eklemeler geliştirici rehberi içinde yeni eklentilerin hızlı anlaşılması ve doğru parametrelerle kullanılabilmesi için tasarlanmıştır. Aşağıdaki bölümde (örnek eklenti) orijinal içerik korunmuştur.
## Örnek: Tam Bir Test Eklentisi

Aşağıda proje içinde doğrudan kullanılabilecek minimal, test edilebilir bir TestPlugin örneği bulunmaktadır. Bu dosyayı [`patternlab/plugins/my_test.py`](patternlab/plugins/my_test.py:1) olarak ekleyebilirsiniz.

```python
# python
from patternlab.plugin_api import TestPlugin, BytesView, TestResult

class MyThresholdTest(TestPlugin):
    """Basit eşik tabanlı monobit benzeri test örneği."""

    requires = ["bits"]

    def describe(self) -> str:
        return "my_threshold_test"

    def run(self, data: BytesView, params: dict) -> TestResult:
        bits = data.bit_view()
        ones = sum(bits)
        n = len(bits)
        threshold = float(params.get("threshold", 0.5))
        passed = True if n == 0 else (ones / n) > threshold
        metrics = {"ones": ones, "total_bits": n, "threshold": threshold}
        return TestResult(test_name=self.describe(), passed=passed, p_value=None, metrics=metrics)
```

## Örnek Unit Test

Eklentinizi doğrulamak için pytest ile basit bir test yazın. Aşağıdaki örnek dosyayı [`tests/test_my_threshold.py`](tests/test_my_threshold.py:1) olarak oluşturabilirsiniz.

```python
# python
from patternlab.plugins.my_test import MyThresholdTest
from patternlab.plugin_api import BytesView

def test_my_threshold_pass():
    plugin = MyThresholdTest()
    # örnek bit dizisi: 6 bit, 5 tane 1 -> oran 0.833
    data = BytesView(b'\xf8')  # 11111000 (örnek)
    result = plugin.run(data, {"threshold": 0.7})
    assert result.passed is True
    assert result.metrics["ones"] >= 5

def test_my_threshold_fail():
    plugin = MyThresholdTest()
    data = BytesView(b'\x0f')  # 00001111 (oran 0.5)
    result = plugin.run(data, {"threshold": 0.6})
    assert result.passed is False
```

## Test ve CI Entegrasyonu

- Yeni eklentiyi ekledikten sonra `pytest` ile testleri çalıştırın.
- Eklentinin bağımlılıkları varsa bunları `pyproject.toml` veya `docs/requirements.txt` içine ekleyin.
- Otomatik test çalıştırma için GitHub Actions iş akışlarına test adımı ekleyin (ör: `pytest` çağrısı).

Ek referansler:
- Eklenti API detayları: [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1)
- Mevcut eklenti örnekleri: [`patternlab/plugins/monobit.py`](patternlab/plugins/monobit.py:1)
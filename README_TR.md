[Click for the English version](./README.md)

# Pattern Analyzer

Pattern Analyzer, ikili (binary) verileri analiz etmek için Python'da yazılmış kapsamlı ve eklenti tabanlı bir çerçevedir. Herhangi bir ikili veri kaynağına istatistiksel testler, kriptografik analizler ve yapısal format tespiti uygulamak için güçlü bir motor sağlar.

## Özellikler

- **Genişletilebilir Eklenti Mimarisi**: Kolayca yeni istatistiksel testler, veri dönüştürücüler veya görselleştiriciler ekleyin.
- **Zengin Eklenti Kütüphanesi**: Aşağıdakiler için çok çeşitli yerleşik eklentilerle birlikte gelir:
  - **İstatistiksel Analiz**: NIST benzeri testler (Monobit, Runs, FFT), Dieharder'dan esinlenilmiş testler ve Hurst Exponent ve Entropi gibi gelişmiş metrikler.
  - **Kriptografik Analiz**: ECB modu şifrelemesini, tekrarlayan anahtar XOR desenlerini algılar ve AES S-box'ları gibi bilinen sabitleri arar.
  - **Yapısal Analiz**: ZIP, PNG ve PDF gibi formatlar için temel ayrıştırıcılar.
  - **Makine Öğrenmesi**: Anomali tespiti için Autoencoder, LSTM ve önceden eğitilmiş sınıflandırıcılar kullanır.
- **Çoklu Arayüzler**: Pattern Analyzer'ı istediğiniz gibi kullanın:
  - Betikleme ve otomasyon için **Komut Satırı Arayüzü (CLI)**.
  - Etkileşimli analiz ve görselleştirme için **Web Kullanıcı Arayüzü (Streamlit)**.
  - Terminal tabanlı etkileşim için **Metin Tabanlı Kullanıcı Arayüzü (TUI)**.
  - Pattern Analyzer'ı diğer hizmetlere entegre etmek için **REST API (FastAPI)**.
- **Yüksek Performanslı Motor**: Güvenlik ve kararlılık için paralel test yürütmeyi, büyük dosyalar için akış (streaming) analizini ve sanal alanlı (sandboxed) eklenti yürütmeyi destekler.

## Kurulum

Pattern Analyzer'ı sanal bir ortamda kurmanız önerilir.

```bash
# Depoyu klonlayın
git clone https://github.com/edgetype/pattern-analyzer.git
cd pattern-analyzer

# Sanal bir ortam oluşturun ve etkinleştirin
python -m venv .venv
# Windows'ta: .venv\Scripts\activate
# macOS/Linux'ta: source .venv/bin/activate

# Paketi tüm isteğe bağlı bağımlılıklarla birlikte düzenlenebilir modda kurun
pip install -e .[test,ml,ui]
```
İsteğe bağlı bağımlılıklar:
- `test`: `pytest` ile test paketini çalıştırmak için.
- `ml`: Makine öğrenmesi tabanlı eklentiler için (TensorFlow, scikit-learn).
- `ui`: Streamlit web arayüzü ve Textual TUI için.

## Hızlı Başlangıç

### Komut Satırı Arayüzü (CLI)

**Standart Analiz**

Bir ikili dosyayı varsayılan test setiyle analiz edin ve raporu kaydedin.

```bash
patternanalyzer analyze test.bin --out report.json
```

Odaklanmış bir analiz için belirli bir yapılandırma profili kullanın (örneğin, kriptografik testler).

```bash
patternanalyzer analyze encrypted.bin --profile crypto --out crypto_report.json
```

**Keşif Modu (Discovery Mode)**

Verilerinize ne tür bir dönüşüm uygulanmış olabileceğini bilmiyorsanız `--discover` modunu kullanın. Bu mod, tek baytlık XOR anahtarları gibi yaygın desenleri otomatik olarak bulmaya çalışır ve en olası adayları raporlar.

```bash
patternanalyzer analyze secret.bin --discover --out discover_report.json
```
Çıktı dosyası `discover_report.json`, potansiyel dönüşümlerin bir listesini ve sonuç verisinin bir önizlemesini içerecektir.

### Kullanıcı Arayüzleri (Web & Terminal)

**Web Arayüzü (Streamlit)**

Dosyaları yüklemek ve sonuçları görselleştirmek için etkileşimli bir web arayüzü başlatın.

```bash
patternanalyzer serve-ui
```

**Terminal Arayüzü (TUI)**

Doğrudan konsolunuzda analiz yapmak için terminal tabanlı bir arayüz başlatın.

```bash
patternanalyzer tui
```

### Python API

Programatik olarak bir analiz işlem hattı çalıştırın.

```python
from patternanalyzer.engine import Engine

# Analiz motorunu başlat
engine = Engine()

# Bir dosyadan veri yükle
with open("test.bin", "rb") as f:
    data_bytes = f.read()

# Bir analiz yapılandırması tanımla
# Bu örnek, monobit testini çalıştırmadan önce basit bir XOR dönüşümü uygular
config = {
    "transforms": [{"name": "xor_const", "params": {"xor_value": 127}}],
    "tests": [{"name": "monobit", "params": {}}],
    "fdr_q": 0.05 # Yanlış Keşif Oranı (FDR) anlamlılık seviyesini ayarla
}

# Analizi çalıştır
output = engine.analyze(data_bytes, config)

# Sonuçları yazdır
import json
print(json.dumps(output, indent=2))
```

## Proje Yapısı

```
pattern-analyzer/
├── patternanalyzer/               # Çerçevenin ana kaynak kodu
│   ├── plugins/              # Yerleşik analiz ve dönüşüm eklentileri
│   ├── __init__.py
│   ├── engine.py             # Çekirdek analiz motoru
│   ├── plugin_api.py         # Eklentiler için temel sınıflar (Test, Transform, Visual)
│   ├── cli.py                # Click tabanlı Komut Satırı Arayüzü
│   ├── api.py                # FastAPI tabanlı REST API
│   ├── tui.py                # Textual tabanlı Terminal Kullanıcı Arayüzü
│   └── ...
├── app.py                    # Streamlit Web Kullanıcı Arayüzü
├── docs/                     # MkDocs için dokümantasyon dosyaları
├── tests/                    # Pytest birim ve entegrasyon testleri
├── pyproject.toml            # Proje üst verileri ve bağımlılıklar
└── README.md
```

## Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen bir "issue" açmaktan veya bir "pull request" göndermekten çekinmeyin.

1.  Depoyu "fork"layın.
2.  Yeni bir özellik dalı oluşturun (`git checkout -b feature/my-new-feature`).
3.  Değişikliklerinizi uygulayın ve testler ekleyin.
4.  Tüm testlerin geçtiğinden emin olun (`pytest`).
5.  Bir "pull request" gönderin.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
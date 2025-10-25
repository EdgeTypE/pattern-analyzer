# Getting Started

Bu sayfa projeyi hızlıca kurup çalıştırmak için gerekli adımları içerir.

Önkoşullar
- Python 3.10+ kurulu olmalı
- Depolama kökü: proje dizini (bkz. [`README.md`](README.md:1))

Kurulum (geliştirme)
```bash
# sanal ortam
python -m venv .venv
.venv/Scripts/activate

# proje bağımlılıkları (geliştirme)
pip install -e .[dev]
pip install mkdocs mkdocs-material
```

Hızlı CLI örneği
```bash
# örnek yapılandırma: [`docs/configs/example.yml`](docs/configs/example.yml:1)
patternlab analyze test.bin -c docs/configs/example.yml -o report.json
```

Programatik kullanım
```python
from patternlab.engine import Engine
engine = Engine()
with open("test.bin","rb") as f:
    data = f.read()

config = {
  "transforms": [{"name":"xor_const","params":{"xor_value":55}}],
  "tests": [{"name":"monobit","params":{"alpha":0.01}}]
}
out = engine.analyze(data, config)
print(out["scorecard"])
```

Yerel dokümantasyon geliştirme
```bash
# MkDocs geliştirme sunucusu (canlı yeniden yükleme)
mkdocs serve
# yayın (GitHub Pages)
mkdocs gh-deploy
```

Daha fazla örnek konfigürasyon için bkz. [`docs/configs/example.yml`](docs/configs/example.yml:1) ve [`docs/configs/example.json`](docs/configs/example.json:1).
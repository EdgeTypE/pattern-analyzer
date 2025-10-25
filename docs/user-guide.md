# User Guide

Bu kılavuz kullanıcı akışlarını, CLI ve API örnek senaryolarını içerir.

Bölümler:
- Hızlı kullanım
- Gelişmiş konfigürasyon
- Pipeline örnekleri
- Hata ayıklama

Hızlı kullanım
CLI ile tek dosya analizi:
```bash
patternlab analyze input.bin -c docs/configs/example.yml -o report.json
```

CLI opsiyonları için bkz. [`patternlab/cli.py`](patternlab/cli.py:1).

Programatik kullanım (Python):
```python
from patternlab.engine import Engine
engine = Engine()
with open("input.bin","rb") as f:
    data = f.read()
config = {"tests":[{"name":"monobit","params":{"alpha":0.01}}]}
out = engine.analyze(data, config)
print(out["scorecard"])
```

Gelişmiş konfigürasyon
Örnek transform + test pipeline:
```yaml
transforms:
  - name: xor_const
    params:
      xor_value: 55
tests:
  - name: monobit
    params: { alpha: 0.01 }
fdr_q: 0.05
```

Bu örnek dosya: [`docs/configs/example.yml`](docs/configs/example.yml:1).

Plugin kullanımı ve geliştirme için bkz. [`docs/plugin-developer-guide.md`](docs/plugin-developer-guide.md:1).

Hata ayıklama
- Verbose log: `patternlab analyze --verbose ...` (CLI desteğini kontrol edin: [`patternlab/cli.py`](patternlab/cli.py:1)).
- Testler: `pytest -k monobit -q`

Yayınlanan raporu inceleyin: `reports/report.html` veya engine çıktısındaki `results` anahtarına bakın.

Daha fazla örnek ve senaryolar için bkz. [`docs/test-reference.md`](docs/test-reference.md:1).
# Config Örnekleri

Bu dizin, PatternLab için JSON ve YAML formatında örnek konfigürasyon dosyaları içerir.

Dosyalar:
- [`docs/configs/example.json`](docs/configs/example.json:1) — JSON örneği
- [`docs/configs/example.yml`](docs/configs/example.yml:1) — YAML örneği

Açıklama (alanlar):
- transforms: Sıralı dönüşümler. Her öğe string veya {"name": .., "params": {...}} olabilir.
- tests: Çalıştırılacak testler listesi. Her öğe string veya {"name": .., "params": {...}} olabilir.
- fdr_q: FDR düzeltmesi için q (ör. 0.05).
- visuals: Görsel eklentiler için parametre haritası (örn. {"fft_placeholder": {"mime": "image/svg+xml"}}).
- html_report: Engine tarafından yazılacak minimal HTML raporun yolu.
- log_path: JSONL formatında test log satırlarının yazılacağı dosya yolu.

Kullanım - CLI:

patternlab analyze ./test.bin -c docs/configs/example.json -o report.json

Kullanım - Programatik:

from patternlab.engine import Engine
engine = Engine()
with open("test.bin","rb") as f:
    out = engine.analyze(f.read(), config)

Notlar:
- YAML dosyaları yüklemek için PyYAML gerekli olabilir.
- Config içindeki test girdi formatları CLI tarafından normalize edilir (bakınız [`patternlab/cli.py`](patternlab/cli.py:1)).
- Daha fazla örnek gerektiğinde bu dizine yeni dosyalar ekleyin.
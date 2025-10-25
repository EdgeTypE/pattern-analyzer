# PatternLab Dokümantasyonu

Bu site PatternLab projesi için kapsamlı kullanım, geliştirici rehberi ve test referansı sağlar.

Hızlı erişim:
- [`Getting Started`](docs/getting-started.md:1)
- [`User Guide`](docs/user-guide.md:1)
- [`Plugin Developer Guide`](docs/plugin-developer-guide.md:1)
- [`API Reference`](docs/api-reference.md:1)
- [`Test Reference`](docs/test-reference.md:1)
- Konfig örnekleri: [`docs/configs/example.yml`](docs/configs/example.yml:1) ve [`docs/configs/example.json`](docs/configs/example.json:1)

Yerel olarak siteyi çalıştırma
```bash
# Gerekli paketleri kurun (tercihen virtualenv içinde)
pip install mkdocs mkdocs-material

# Geliştirme sunucusu
mkdocs serve
```

GitHub Pages'e hızlı yayım
```bash
# ilk kez deploy için repo ayarlarını kontrol edin
mkdocs gh-deploy
```

Read the Docs ile yayınlama
- Projeyi Read the Docs'da etkinleştirin.
- Gerekirse `requirements-docs.txt` veya `docs/requirements.txt` dosyası ekleyin.
- (Opsiyonel) RTD yapılandırması için `readthedocs.yml` eklenebilir.

Mevcut Markdown içerik kaynakları
- Eklenti rehberi: [`docs/plugin-developer-guide.md`](docs/plugin-developer-guide.md:1)
- Test referansı: [`docs/test-reference.md`](docs/test-reference.md:1)
- Konfig örnekleri: [`docs/configs/README.md`](docs/configs/README.md:1)

Bu sayfa, MkDocs yapılandırması olan [`mkdocs.yml`](mkdocs.yml:1) dosyası ile eşleşir. Bir sonraki adım olarak "Getting Started" ve "User Guide" sayfalarını zenginleştireceğim.
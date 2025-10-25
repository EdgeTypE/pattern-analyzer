# İstatistiksel Test Referansı (Detaylı)

Bu belge, proje içindeki istatistiksel test eklentileri için:
- kullanılan istatistiksel formüller,
- NIST SP 800‑22 ile uyumluluk/benzerlik derecesi,
- kodda tanımlı minimum veri uzunluğu / önerilen minimumlar,
- SciPy veya numpy gibi opsiyonel bağımlılıklar ve SciPy yoksa kullanılan alternatif hesaplama yolları,
- kısa örnek çıktı/örnek veri açıklamalarını içerir.

Genel notlar
- Tüm testler [`patternlab/plugin_api.py`](patternlab/plugin_api.py:1) içindeki `TestResult` yapısını döndürür.
- Engine yalnızca `category == "statistical"` ve `p_value is not None` olan sonuçları FDR hesaplarına dahil eder.
- `requires` alanı testin çalışması için gerekli BytesView görünümlerini belirtir (örn. `bits`, `text`, `bytes`).
- "NIST uyumluluk seviyesi"nden kastımız: testin NIST SP 800‑22'de birebir yer alıp almadığı, veya NIST yaklaşımına ne kadar yakın olduğu (birebir = "uyumlu", benzer/özet = "inspire").

Monobit Test
- Dosya: [`patternlab/plugins/monobit.py`](patternlab/plugins/monobit.py:1)
- Amaç: Bit dizisindeki 1'lerin sayısının beklenen frekansta olup olmadığını test etmek.
- Kategori: statistical (NIST SP 800‑22 ile uyumlu / eşdeğer)
- Kod gereksinimleri: `requires = ['bits']`
- Kod parametreleri / minimumlar:
  - `alpha` (float, default 0.01)
  - Kodda açık bir minimum yok; ancak NIST ve pratik uygulamalarda güvenilir sonuç için önerilen minimum n ≥ 100 - 200 bit'tir.
- İstatistiksel formül:
  - S = ones_count
  - $$z = \frac{2S - n}{\sqrt{n}}$$
  - p-değeri (iki taraflı): $$p = 2(1 - \Phi(|z|))$$ veya yaygın pratikte $$p = \operatorname{erfc}\!\left(\frac{|z|}{\sqrt{2}}\right)$$
  - Kod: z hesaplanır ve normal dağılımın CDF'si (Abramowitz–Stegun yaklaşık CDF) kullanılarak p elde edilir.
- SciPy bağımlılığı: yok (kod kendi normal CDF yaklaşımını kullanır).
- Alternatifler: SciPy mevcutsa `scipy.stats.norm.sf` veya `scipy.stats.norm.cdf` daha hassas sonuç verir.
- Örnek:
  - Girdi: 100 bit, ones_count = 52 → z ≈ (104−100)/10 = 0.4 → p ≈ 0.688 (pass for alpha=0.01)
- Çıktı örneği (TestResult): metrics={"ones_count": S, "total_bits": n}, z_score, p_value.

Block Frequency Test
- Dosya: [`patternlab/plugins/block_frequency_test.py`](patternlab/plugins/block_frequency_test.py:1)
- Amaç: Diziyi M boyutlu bloklara ayırıp blok başına 1 oranlarını karşılaştırmak.
- Kategori: statistical (NIST benzeri; basitleştirilmiş NIST yaklaşımı uygulanmış)
- Kod gereksinimleri: `requires = ['bits']`
- Kod parametreleri / minimumlar:
  - `block_size` (int, default 8). Kodda blok sayısı = floor(n / M). Eğer blok_count == 0 → trivial p_value = 1.0 döner.
  - Öneri (NIST'e benzer): en iyi uygulama için block_count ≳ 10–20; yani n ≳ 10*M.
- İstatistiksel formül (doküman ve kod uyumu):
  - Her blok için oran \(p_i = \frac{\text{ones}_i}{M}\).
  - Test istatistiği (kodda kullanılan form):
    $$\chi^2 = 4M \sum_{i=1}^{N} (p_i - 1/2)^2$$
    burada \(N\) blok sayısı, \(M\) blok büyüklüğü.
  - p-değeri: eğer SciPy varsa chisq dağılımının sağ kuyruk fonksiyonu:
    $$p = \mathrm{chi2.sf}(\chi^2, \; \text{df}=N)$$
- SciPy bağımlılığı ve alternatif:
  - Kodda `scipy.stats.chi2.sf` kullanılmaya çalışılır.
  - SciPy yoksa fallback: `math.erfc(sqrt(chi_square/2))`. Eğer bu da başarısız olursa en basit approx `1 - exp(-chi/2)` kullanılır (kodda bulunur).
- Örnek: M=8, n=800 → N=100 blok; chi^2 hesaplanıp scipy ile p elde edilir.
- Not: Kodda `block_count == 0` durumda test trivial pass olarak döner.

Runs Test (Wald–Wolfowitz)
- Dosya: [`patternlab/plugins/runs_test.py`](patternlab/plugins/runs_test.py:1)
- Amaç: Ardışık aynı değer bloklarının (runs) beklenen sayısıyla karşılaştırma.
- Kategori: statistical (NIST ile benzer mantık)
- Kod gereksinimleri: `requires = ['bits']`
- Kod parametreleri / minimumlar:
  - `min_bits` (int, default 20). Kodda total_bits < min_bits → trivial pass (p=1.0).
  - NIST benzeri uygulamalarda güvenli sonuç için genelde n ≥ 100 önerilir; ancak kod bunu daha düşük tutuyor.
- İstatistiksel formül:
  - n1 = ones, n2 = zeros, n = n1 + n2
  - Beklenen runs:
    $$E(R) = \frac{2 n_1 n_2}{n} + 1$$
  - Varyans (kodda kullanılan yaklaşık formül):
    $$\operatorname{Var}(R)=\frac{2 n_1 n_2 (2 n_1 n_2 - n)}{n^2 (n - 1)}$$
  - Z-score:
    $$z = \frac{R - E(R)}{\sqrt{\operatorname{Var}(R)}}$$
  - İki taraflı p:
    $$p = 2(1 - \Phi(|z|))$$
- SciPy bağımlılığı: yok (kod kendi A&S normal CDF yaklaşımını kullanır); SciPy varsa `scipy.stats.norm.sf` tercih edilebilir.
- Örnek çıktı: metrics={"ones":n1,"zeros":n2,"runs":R,"total_bits":n}, z_score, p_value.

Serial Test
- Dosya: [`patternlab/plugins/serial_test.py`](patternlab/plugins/serial_test.py:1)
- Amaç: m-gram frekansları üzerinden dizinin istatistiksel yapısını kontrol etmek (m=1..max_m).
- Kategori: statistical (NIST benzeri; NIST serial test'e benzer yaklaşımlar vardır)
- Kod gereksinimleri: `requires = ['bits']`
- Parametreler:
  - `max_m` (int, default 4)
  - Öneri: m arttıkça gerekli n hızlıca yükselir; en azından \(n \gg 2^m\) olacak şekilde veri gereklidir.
- İstatistik ve p-değeri:
  - Her m için frekanslardan chi-square benzeri istatistikler hesaplanır.
  - p-değerleri için genelde ki-kare dağılımının sağ kuyruğu veya NIST eşdeğer hesaplar kullanılır.
- SciPy bağımlılığı: varsa `scipy.stats.chi2` ile p hesaplanabilir; yoksa proje içi yaklaşık yöntemler veya basitleştirilmiş erfc/exp yöntemleri kullanılabilir.
- Not: Kod, her m için ayrı p hesapları döndürür ve en düşük p overall olarak raporlanır.

Autocorrelation (diagnostic)
- Dosya: [`patternlab/plugins/autocorrelation.py`](patternlab/plugins/autocorrelation.py:1)
- Amaç: Bitleri +1/−1'e çevirip lag bazlı otokorelasyon hesaplanır; diagnostic amaçlıdır, formal p-value üretmez.
- Kategori: diagnostic
- Kod gereksinimleri: bit_view, numpy opsiyonel
- Parametreler / minimumlar:
  - `lag_max` (default kod: min(64, max(1, n//4))). Kod, n==0 durumunda error (TestResult ile passed=False, p_value=None).
- Hesaplama yolları:
  - Eğer numpy mevcutsa FFT tabanlı hızlı otokorelasyon kullanılır (`numpy.fft.rfft` vb.) — O(N log N).
  - NumPy yoksa naive O(N * lag_max) döngüsü ile hesaplanır.
- Normalizasyon: kod lag0 değerine bölerek \(\text{autocorr}[0]=1.0\) olacak şekilde normalize eder.
- Örnek çıktı: metrics={"autocorr":[1.0, 0.02, ...], "lags":[0,1,2...], "n":n, "lag_max":lag_max}.

Linear Complexity (diagnostic)
- Dosya: [`patternlab/plugins/linear_complexity.py`](patternlab/plugins/linear_complexity.py:1)
- Amaç: Berlekamp–Massey ile bit dizisinin GF(2) üzerindeki lineer karmaşıklığını hesaplar.
- Kategori: diagnostic (NIST lineer kompleksite testine benzer olsa da projede diagnostic olarak ele alınmış olabilir)
- Kod gereksinimleri: `requires = ['bits']`
- Çıktı / notlar:
  - Berlekamp–Massey algoritması doğrudan lineer kompleksite L döndürür.
  - NIST SP 800‑22'de linear complexity testindeki gibi L için normalize istatistik ve p-değeri hesaplanabilir; kod mevcut haliyle genelde diagnostic sonuç döndürüyor (p_value=1.0 ile uyumluluk amacıyla).
- SciPy bağımlılığı: yok tipik olarak (algoritma doğrudan bit düzeyinde çalışır).

Binary Matrix Rank
- Dosya: [`patternlab/plugins/binary_matrix_rank.py`](patternlab/plugins/binary_matrix_rank.py:1)
- Amaç: Bit dizisini m×m matrislere ayırıp GF(2) rank dağılımının beklenen dağılıma göre sapmasını test eder.
- Kategori: statistical (NIST'e benzer)
- Kod gereksinimleri: `requires = ['bits']`
- Parametreler / minimumlar:
  - `matrix_dim` (default 32), `min_matrices` (default 8)
  - Kodda yetersiz matris sayısı durumunda trivial pass dönebilir.
- İstatistik: matris başına rank hesaplanır; beklenen full-rank oranlarına göre chi-square benzeri test uygulanır.
- SciPy bağımlılığı: rank hesaplaması GF(2) üzerinde yapılır (özel implemantasyon); istatistik için SciPy varsa chi2 kullanımı tercih edilebilir.

Cumulative Sums (Cusum)
- Dosya: [`patternlab/plugins/cusum.py`](patternlab/plugins/cusum.py:1)
- Amaç: Bitleri +1/-1'e çevirip kümülatif toplamın maksimum mutlak değerine göre sapmayı değerlendirir.
- Kategori: statistical (NIST benzeri)
- Kod gereksinimleri: `requires = ['bits']`
- Parametreler / minimumlar:
  - `min_bits` (default 100)
- İstatistik: maksimum kümülatif toplam değeri \(S_{\max}\) alınır; NIST tarzı yaklaşık p hesapları kullanılabilir.
- SciPy bağımlılığı: opsiyonel; SciPy yoksa yaklaşık erfc/normal cdf yaklaşımları kullanılabilir.

FFT Spectral (diagnostic)
- Dosya: [`patternlab/plugins/fft_spectral.py`](patternlab/plugins/fft_spectral.py:1)
- Amaç: +1/−1 dönüşümünden sonra FFT spektrumu üzerinden güçlü tepe/garip frekans bileşenlerini tespit etmek.
- Kategori: diagnostic
- Kod gereksinimleri: `requires = ['bits']` ; numpy opsiyonel (FFT için)
- Hesaplama yolları:
  - Numpy yoksa fallback veya daha basit DFT/pürüzsüzleştirme yolları uygulanabilir; kod genelde numpy presence'ı denemeye yatkındır.
- Çıktı: tepe SNR, tepe indisi, gürültü tabanı ve profil.

Longest Run of Ones in a Block
- Dosya: [`patternlab/plugins/longest_run.py`](patternlab/plugins/longest_run.py:1)
- Amaç: Her blok için en uzun 1 koşusunu sınıflandırır ve kategori histogramı üzerinden chi-square benzeri test uygular.
- Kategori: statistical (NIST'e benzer uygulama)
- Kod gereksinimleri: `requires = ['bits']`
- Parametreler / minimumlar:
  - `block_size` (default 8), `min_blocks` (default 8)
- Not: Yetersiz blok sayısında kod trivial pass dönebilir; öneri NIST benzeri sonuç için blok sayısı daha büyük tutulmalıdır.

Bağımlılıklar ve alternatif hesaplama yöntemleri
- SciPy:
  - Kullanılan yerler: özellikle chi-square sağ-kuyruk değerleri için (`scipy.stats.chi2.sf`) ve gerektiğinde normal dağılım fonksiyonları.
  - Projede SciPy yoksa:
    - Normal CDF için Abramowitz–Stegun yaklaşık formülleri (monobit, runs) kullanılır.
    - Chi-square için basit yaklaşımlar: `erfc(sqrt(chi/2))` veya `1 - exp(-chi/2)` gibi yaklaşık dönüşümler kullanılır (kodda güvenlik amaçlı fallback blokları bulunur).
- NumPy:
  - FFT/otocorrelation hesapları için kullanılması performans açısından tercih edilir. NumPy yoksa naive O(N*lag) yöntemleri uygulanır.
- Öneri: Tam istatistiksel doğruluk ve karşılaştırılabilirlik için SciPy ve NumPy kurulması tavsiye edilir.

Minimum veri uzunlukları (özet)
- Kodda tanımlı minimumlar (koda bakınız; bazı testler trivial pass döner):
  - Runs: `min_bits` default 20 (kodda)
  - Cusum: `min_bits` default 100 (kodda)
  - Block Frequency: blok sayısı 0 ise trivial pass; practical öneri block_count ≳ 10
  - Linear Complexity, Autocorrelation, FFT: diagnostic, fakat anlamsız kısa veriler hata veya trivial sonuç üretebilir (ör. n==0 durumunda autocorr error döner).
- Pratik/NIST önerileri:
  - Çoğu NIST testi için n ≥ 100–200 önerilir; m-gram bazlı testlerde \(n \gg 2^m\) gereklidir.

Örnek veri seti ve çıktı notları
- Monobit küçük örnek:
  - Girdi (bits): 10110010... (n=100), ones_count=52
  - TestResult.metrics → {"ones_count":52,"total_bits":100}, z_score, p_value ≈ 0.68
- Block Frequency örnek:
  - block_size=8, n=800 → block_count=100, hesaplanan chi^2 ve p döndürülür.
- Autocorrelation örnek:
  - metrics.autocorr → [1.0, 0.02, -0.01, ...], lags → [0,1,2,...]
- Genel: TestResult yapısı tüm testler için tutarlıdır: test_name, passed, p_value (veya None), p_values (per-test), metrics, opsiyonel z_score.

Kaynaklar ve ileri okuma
- NIST SP 800‑22 “A Statistical Test Suite for Random and Pseudorandom Number Generators for Cryptographic Applications” — temel referans ve test açıklamaları.
- Projedeki eklenti implementasyonları:
  - [`patternlab/plugins/monobit.py`](patternlab/plugins/monobit.py:1)
  - [`patternlab/plugins/block_frequency_test.py`](patternlab/plugins/block_frequency_test.py:1)
  - [`patternlab/plugins/runs_test.py`](patternlab/plugins/runs_test.py:1)
  - [`patternlab/plugins/autocorrelation.py`](patternlab/plugins/autocorrelation.py:1)
- Konfigürasyon örnekleri: [`docs/configs/example.json`](docs/configs/example.json:1) ve geliştirici rehberi `docs/plugin-developer-guide.md`.

Bu dosya, mevcut kod tabanındaki testlerin hem uygulama (kod) hem de istatistiksel referans açısından eksiksiz ve açık bir özeti olarak güncellendi. Eğer daha ayrıntılı NIST‑eşdeğeri tablolar veya her test için genişletilmiş matematiksel türetimler isteniyorsa, bunlar ayrı bir genişletme dokümanında sağlanmalıdır.
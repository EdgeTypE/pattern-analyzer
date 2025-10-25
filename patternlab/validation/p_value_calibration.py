# P-değeri kalibrasyon ve uniformluk doğrulama araçları
# Bu modül:
# - deterministik "stream" üreteçleri (AES-CTR / ChaCha20 benzeri fallback'lar olarak hash-CTR kullanır)
# - p-değerlerini toplar, QQ verisini üretir
# - Kolmogorov-Smirnov (KS) testi ile U(0,1) uygunluğunu yaklaşık hesaplar
# - Sonuçları CSV olarak kaydetme seçeneği sağlar
#
# Not: Gerçek AES-CTR / ChaCha20 implementasyonları mevcutsa bunlar yerine geçirilebilir.
from __future__ import annotations

import csv
import math
import os
import hashlib
import random
from typing import Callable, Dict, List, Tuple, Optional


def _hash_ctr_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Basit deterministik stream üretici: hash(key||nonce||counter) şeklinde çalışır.
    Gerçek AES-CTR yerine kullanılabilecek, deterministik ve tekrarlanabilir bir fallback'tır.
    """
    out = bytearray()
    counter = 0
    while len(out) < length:
        blob = key + nonce + counter.to_bytes(8, "big")
        h = hashlib.sha256(blob).digest()
        out.extend(h)
        counter += 1
    return bytes(out[:length])


def generate_streams(
    count: int,
    length: int,
    mode: str = "aes_ctr",
    seed: Optional[int] = None,
) -> List[bytes]:
    """Belirtilen sayıda deterministik 'random' stream üretir.

    mode:
      - "aes_ctr" veya "chacha20": her ikisi de aynı hash-CTR fallback'ını kullanır (ayrışma için farklı key/NONCE).
      - "python": python.Random tabanlı deterministik byte akışı (seed ile tekrarlanabilir).

    Bu fonksiyon gerçek kriptografik kütüphaneler olmadan test amaçlı deterministik akış sağlar.
    """
    streams: List[bytes] = []
    rng = random.Random(seed) if seed is not None else random.Random(0xC0FFEE)
    for i in range(count):
        if mode in ("aes_ctr", "chacha20"):
            # Key ve nonce'ları mode ve index'e göre türet (deterministik)
            key = hashlib.sha256(f"{mode}-key-{i}".encode("utf-8")).digest()
            nonce = hashlib.sha256(f"{mode}-nonce-{i}".encode("utf-8")).digest()[:12]
            streams.append(_hash_ctr_stream(key, nonce, length))
        elif mode == "python":
            # python RNG ile bytes üret
            b = bytearray(rng.getrandbits(8) for _ in range(length))
            streams.append(bytes(b))
        else:
            raise ValueError(f"Unknown mode: {mode}")
    return streams


def compute_pvalues_from_streams(
    streams: List[bytes], test_func: Callable[[bytes], float]
) -> List[float]:
    """Her stream için test_func çağırarak p-değerleri toplar.
    test_func(stream_bytes) -> p-value (0..1)
    """
    pvals: List[float] = []
    for s in streams:
        p = float(test_func(s))
        # güvenlik: p değeri sınırla
        if p < 0.0:
            p = 0.0
        if p > 1.0:
            p = 1.0
        pvals.append(p)
    return pvals


def qq_data(p_values: List[float]) -> Tuple[List[float], List[float]]:
    """QQ-plot için teorik ve gözlenen nicelleştirilmiş kuantilleri döner.

    Returns (theoretical_quantiles, empirical_quantiles) where both lists length = n
    """
    n = len(p_values)
    if n == 0:
        return [], []
    sorted_p = sorted(p_values)
    theoretical = [(i + 1) / (n + 1) for i in range(n)]
    empirical = sorted_p
    return theoretical, empirical


def _ks_pvalue_approx(d: float, n: int, max_terms: int = 100) -> float:
    """Kolmogorov-Smirnov p-değerinin asimptotik yaklaşık hesaplaması.
    Kullanılan formül:
      p ≈ 2 * sum_{k=1..∞} (-1)^(k-1) * exp(-2 * k^2 * x^2)
    burada x = d * sqrt(n)
    Bu ifade, P( sqrt(n) D_n > x ) için sağkalım fonksiyonunu verir.
    """
    if n <= 0:
        return 1.0
    if d <= 0:
        return 1.0
    x = d * math.sqrt(n)
    s = 0.0
    for k in range(1, max_terms + 1):
        term = (-1) ** (k - 1) * math.exp(-2.0 * (k * k) * (x * x))
        s += term
        # küçük terimler için dur
        if abs(term) < 1e-12:
            break
    p = 2.0 * s
    # sınırla
    p = max(0.0, min(1.0, p))
    return p


def ks_test_uniform(p_values: List[float]) -> Dict[str, float]:
    """p_values dizisinin U(0,1) ile uyumlu olup olmadığını Kolmogorov-Smirnov testi ile değerlendirir.

    Döndürür:
      {
        "D": D_statistic,
        "p_value": p_value_approx
      }
    """
    n = len(p_values)
    if n == 0:
        return {"D": 0.0, "p_value": 1.0}
    sorted_p = sorted(p_values)
    # ECDF ile teorik CDF (F(x)=x) farkı
    d_plus = max(((i + 1) / n - sorted_p[i]) for i in range(n))
    d_minus = max((sorted_p[i] - i / n) for i in range(n))
    D = max(d_plus, d_minus)
    p = _ks_pvalue_approx(D, n)
    return {"D": D, "p_value": p}


def save_calibration_csv(
    path: str,
    p_values: List[float],
    qq_theoretical: List[float],
    qq_empirical: List[float],
    ks_result: Dict[str, float],
) -> None:
    """Sonuçları CSV olarak kaydeder. CSV şu sütunları içerir:
      stream_index, p_value, qq_theoretical, qq_empirical
    En sonda KS sonuçları için bir özet satırı eklenir.
    """
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["stream_index", "p_value", "qq_theoretical", "qq_empirical"])
        for i, (p, t, e) in enumerate(zip(p_values, qq_theoretical, qq_empirical)):
            writer.writerow([i, f"{p:.12g}", f"{t:.12g}", f"{e:.12g}"])
        # boş bir satır ve KS özeti
        writer.writerow([])
        writer.writerow(["KS_D", ks_result.get("D")])
        writer.writerow(["KS_pvalue", ks_result.get("p_value")])


def calibrate_p_values(
    *,
    num_streams: int = 100,
    stream_length: int = 1024,
    generator_mode: str = "aes_ctr",
    generator_seed: Optional[int] = None,
    test_func: Optional[Callable[[bytes], float]] = None,
    save_csv: Optional[str] = None,
) -> Dict[str, object]:
    """Ana kalibrasyon fonksiyonu.

    - num_streams: üretilen stream sayısı
    - stream_length: her stream'in byte uzunluğu
    - generator_mode: "aes_ctr" | "chacha20" | "python"
    - generator_seed: deterministik davranış için seed
    - test_func: her stream'e uygulanacak test; eğer None ise varsayılan olarak uniform p-value döndüren
                 sentetik test kullanılır (test amaçlı).
    - save_csv: Eğer belirtilirse sonuç CSV olarak buraya yazılır.

    Döndürür:
      {
        "p_values": [...],
        "qq_theoretical": [...],
        "qq_empirical": [...],
        "ks": {"D": ..., "p_value": ...},
        "num_streams": num_streams,
        "stream_length": stream_length,
      }
    """
    if test_func is None:
        # Varsayılan sentetik test: stream içeriğine bakmadan deterministik 'uniform' p değeri üretir.
        # Bu, kalibrasyon pipeline'ını test etmek için kullanılır.
        def _synthetic_test(_b: bytes, rng_seed_iter=[generator_seed or 0]) -> float:
            # Her çağrıda farklı RNG seed'i kullanarak tekrarlanabilir uniform p-değerleri üretir.
            rng = random.Random(rng_seed_iter[0])
            rng_seed_iter[0] = (rng_seed_iter[0] + 1) & 0xFFFFFFFF
            return rng.random()
        test_func = _synthetic_test

    streams = generate_streams(num_streams, stream_length, mode=generator_mode, seed=generator_seed)
    p_values = compute_pvalues_from_streams(streams, test_func)
    qq_theoretical, qq_empirical = qq_data(p_values)
    ks = ks_test_uniform(p_values)

    if save_csv:
        try:
            save_calibration_csv(save_csv, p_values, qq_theoretical, qq_empirical, ks)
        except Exception:
            # CSV kaydetme hatası nedeniyle pipeline başarısız olmasın
            pass

    return {
        "p_values": p_values,
        "qq_theoretical": qq_theoretical,
        "qq_empirical": qq_empirical,
        "ks": ks,
        "num_streams": num_streams,
        "stream_length": stream_length,
    }
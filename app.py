import streamlit as st
import base64
import pandas as pd
import json
from patternanalyzer.engine import Engine

st.set_page_config(page_title="Pattern Analyzer", layout="wide", page_icon="🔬")

# Modern Custom CSS Theme
st.markdown("""
<style>
/* Global Theme Variables */
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --success-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    --warning-gradient: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
    --danger-gradient: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
    --dark-bg: #0f0f23;
    --card-bg: rgba(255, 255, 255, 0.05);
    --glass-bg: rgba(255, 255, 255, 0.1);
    --border-color: rgba(255, 255, 255, 0.1);
    --text-primary: #ffffff;
    --text-secondary: rgba(255, 255, 255, 0.7);
}

/* Main container styling */
.stApp {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

/* Header styling */
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.5rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 0.5rem;
    letter-spacing: -0.02em;
}

.sub-header {
    color: rgba(255, 255, 255, 0.7);
    text-align: center;
    font-size: 1.1rem;
    margin-bottom: 2rem;
    font-weight: 400;
}

/* Modern card styling */
.modern-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}

.modern-card:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(102, 126, 234, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}

.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.metric-label {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.9rem;
    margin-top: 0.25rem;
}

/* Section headers */
.section-header {
    color: #ffffff;
    font-size: 1.5rem;
    font-weight: 600;
    margin: 1.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid rgba(102, 126, 234, 0.5);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #0f0f23 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stSlider label {
    color: rgba(255, 255, 255, 0.9) !important;
    font-weight: 500;
}

/* Button styling */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 10px;
    color: white;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.stButton > button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: white;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* Select boxes */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
}

/* Expander styling */
.streamlit-expanderHeader {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    color: white !important;
}

/* DataFrame styling */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 0.25rem;
    gap: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

/* Slider styling */
.stSlider > div > div > div {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* File uploader */
.stFileUploader > div {
    background: rgba(255, 255, 255, 0.05);
    border: 2px dashed rgba(102, 126, 234, 0.5);
    border-radius: 12px;
}

.stFileUploader > div:hover {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.1);
}

/* Spinner */
.stSpinner > div {
    border-top-color: #667eea !important;
}

/* Success/Error/Warning messages */
.stSuccess {
    background: rgba(17, 153, 142, 0.2);
    border-left: 4px solid #11998e;
}

.stError {
    background: rgba(238, 9, 121, 0.2);
    border-left: 4px solid #ee0979;
}

.stWarning {
    background: rgba(242, 153, 74, 0.2);
    border-left: 4px solid #F2994A;
}

/* Animation for loading */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 2s infinite;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #7b8eeb 0%, #8a5bb3 100%);
}

/* Status badges */
.status-passed {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.status-failed {
    background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.status-skipped {
    background: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.7);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

engine = Engine()

def run_analysis(config):
    # input_bytes'ı hesaplayalım
    input_bytes = b""
    if config.get('data', {}).get('file'):
        uploaded_file = config['data']['file']
        if uploaded_file is not None:
            input_bytes = uploaded_file.read()
    elif config.get('data', {}).get('text'):
        text = config['data']['text']
        if text:
            # Try to decode as base64, fallback to utf-8 encode
            try:
                input_bytes = base64.b64decode(text)
            except Exception:
                input_bytes = text.encode('utf-8')

    # engine.analyze çağrısı doğru parametrelerle
    result = engine.analyze(input_bytes, config)
    st.session_state['analysis_result'] = result

def format_val(v, lang_code='tr', max_len=50):
    if v is None:
        return "None"
    if isinstance(v, dict):
        items = []
        for kk, vv in v.items():
            if isinstance(vv, (int, float)):
                items.append(f"{kk}: {vv}")
            else:
                items.append(f"{kk}: {str(vv)[:20]}...")
        val_str = ', '.join(items)
        if len(val_str) > max_len:
            val_str = val_str[:max_len] + '...'
        return val_str
    elif isinstance(v, list):
        return ', '.join(map(str, v))[:max_len] + '...' if len(', '.join(map(str, v))) > max_len else ', '.join(map(str, v))
    return str(v)

def main():
    # Language support
    if 'language' not in st.session_state:
        st.session_state.language = "en"
    # TO DO (P3): Load language strings from an external file
    lang = {
        "tr": {
            "main_title": "Pattern Analyzer Analiz Platformu",
            "main_desc": "Bu platform, verilerinizde rastgelelik paternlerini analiz etmek için güçlü istatistiksel testler sunar. Dosya yükleyin veya doğrudan veri girin ve kapsamlı bir analiz raporu elde edin.",
            "results_title": "Analiz Sonuçları",
            "control_panel": "Kontrol Paneli",
            "file_tab": "Dosya",
            "text_tab": "Metin",
            "file_label": "Dosya Seçin",
            "file_help": "Limit 200MB per file • BIN, TXT, DAT",
            "text_label": "Veri Girin",
            "text_placeholder": "Base64 encoded data veya doğrudan metin girin...",
            "test_selection": "Test Seçimi",
            "tests_label": "Çalıştırılacak Testler",
            "tests_help": "Çalıştırılacak testleri seçin. Her test, verinin rastgeleliğini farklı açılardan inceler. Örneğin, monobit testi 0 ve 1'lerin dağılımını kontrol eder.",
            "all_tests": "Tüm Testleri Seç",
            "no_tests": "Hiçbir Test Seçme",
            "transform_selection": "Transform Seçimi",
            "transforms_label": "Uygulanacak Transformlar",
            "transforms_help": "Uygulanacak transformları seçin. Transformlar, veriyi dönüştürerek testlerin hassasiyetini artırabilir, örneğin XOR ile şifreleme paternlerini kırar.",
            "all_transforms": "Tüm Transformları Seç",
            "no_transforms": "Hiçbir Transform Seçme",
            "analysis_settings": "Analiz Ayarları",
            "fdr_label": "FDR Anlamlılık Düzeyi (q)",
            "fdr_help": "FDR (False Discovery Rate) anlamlılık düzeyi. Düşük değer (ör. 0.05) daha katı test anlamına gelir; p-value < q ise test başarısız sayılır.",
            "start_analysis": "Analizi Başlat",
            "clear": "Temizle",
            "analyzing": "Analiz yapılıyor...",
            "analysis_error": "Analiz hatası: {error}",
            "scorecard": "Scorecard",
            "findings": "Bulgular",
            "select_result": "Bir sonuç seçin",
            "selected_details": "Seçilen Sonucun Detayları",
            "visuals": "Görseller",
            "visual_error": "Görsel gösterilemedi ({name}): {error}",
            "visual_format_error": "Görsel formatı yanlış: {name}",
            "no_results": "Analiz sonucu boş veya yok.",
            "language": "Dil",
            "failed_tests": "Başarısız Testler",
            "mean_effect_size": "Ortalama Etki Boyutu",
            "mean_effect_size_desc": "Testlerin etki boyutlarının ortalaması (ör. sapma miktarı). None ise yeterli veri yok veya hesaplanmadı.",
            "p_value_distribution": "P-Değeri Dağılımı",
            "p_value_distribution_desc": "P-değerlerinin istatistikleri (adet, ortalama, medyan vb.). Rastgele veride p-değerleri uniform dağılımlı olmalı.",
            "total_tests": "Toplam Testler",
            "fdr_q": "FDR q",
            "skipped_tests": "Atlanan Testler",
            "skipped_tests_desc": "Atlanan testler: Veri boyutu yetersiz veya önkoşullar sağlanmadı. Detaylar sonuç tablosunda 'reason' sütununda.",
            "run_tests": "Çalıştırılan Testler",
            "test_explanations": {
                "monobit": "Monobit testi: Verideki 0 ve 1'lerin sayısını kontrol eder. Rastgele veride yaklaşık eşit olmalı.",
                "approximate_entropy": "Approximate Entropy: Verinin tahmin edilemezliğini ölçer. Düşük entropi düzenli patern gösterir.",
                "autocorrelation": "Autocorrelation: Verinin kendisiyle gecikmeli korelasyonunu hesaplar. Yüksek değer periyodiklik belirtir.",
                "autoencoder_anomaly": "Autoencoder Anomaly: Makine öğrenmesiyle anomalileri tespit eder.",
                "binary_matrix_rank": "Binary Matrix Rank: Matris rank testi, lineer bağımlılıkları kontrol eder.",
                "block_frequency": "Block Frequency: Bloklardaki frekans dağılımını test eder.",
                "classifier_labeler": "Classifier Labeler: Sınıflandırıcı ile veriyi etiketler.",
                "conditional_entropy": "Conditional Entropy: Koşullu entropi, bağımlılıkları ölçer.",
                "cusum": "Cumulative Sums: Kümülatif toplam testi, sapmaları tespit eder.",
                "dft_spectral_advanced": "DFT Spectral Advanced: Spektral analiz, frekans paternlerini arar.",
                "diehard_3d_spheres": "Diehard 3D Spheres: 3D küre testi (veri yetersizse hata verir).",
                "diehard_birthday_spacings": "Diehard Birthday Spacings: Doğum günü aralık testi.",
                "diehard_overlapping_sums": "Diehard Overlapping Sums: Çakışan toplamlar testi.",
                "dotplot": "Dotplot: Veri paternlerini görselleştirir.",
                "ecb_detector": "ECB Detector: ECB modunda şifreleme paternlerini arar.",
                "fft_spectral": "FFT Spectral: Frekans domain analizi.",
                "frequency_pattern": "Frequency Pattern: Frekans paternleri ve Vigenere anahtar uzunluğu tahmini.",
                "hurst_exponent": "Hurst Exponent: Uzun vadeli bağımlılık ölçüsü.",
                "known_constants_search": "Known Constants Search: Bilinen sabitleri arar.",
                "linear_complexity": "Linear Complexity: Lineer karmaşıklık testi.",
                "longest_run_ones": "Longest Run of Ones: En uzun 1'ler dizisi testi.",
                "lstm_gru_anomaly": "LSTM GRU Anomaly: Zaman serisi anomalileri tespit eder.",
                "lz_complexity": "LZ Complexity: Lempel-Ziv karmaşıklığı.",
                "magic_detector": "Magic Detector: Dosya tipi sihirli baytları arar.",
                "maurers_universal": "Maurer's Universal: Evrensel istatistik testi.",
                "mutual_information": "Mutual Information: Karşılıklı bilgi ölçüsü.",
                "nist_dft_spectral": "NIST DFT Spectral: NIST spektral testi.",
                "non_overlapping_template_matching": "Non-Overlapping Template: Çakışmayan şablon eşleştirme.",
                "overlapping_template_matching": "Overlapping Template: Çakışan şablon eşleştirme.",
                "blocking": "Blocking: Bloklama testi.",
                "quickstat": "Quickstat: Hızlı istatistik özeti.",
                "pdf_structure": "PDF Structure: PDF yapı analizi.",
                "png_structure": "PNG Structure: PNG yapı analizi.",
                "random_excursions": "Random Excursions: Rastgele gezinti testi.",
                "random_excursions_variant": "Random Excursions Variant: Gezinti varyantı.",
                "runs": "Runs: Runs testi, değişim sayısını kontrol eder.",
                "serial": "Serial: Seri korelasyon testi.",
                "testu01_smallcrush": "TestU01 SmallCrush: Küçük ezme test paketi.",
                "transfer_entropy": "Transfer Entropy: Bilgi transferi ölçüsü.",
                "zip_structure": "ZIP Structure: ZIP arşiv yapı analizi.",
            },
            "column_explanations": {
                "test_name": "Test adı",
                "passed": "Geçti mi? (True: Rastgelelik kabul edildi)",
                "p_value": "P-değeri: Düşükse (<0.05) veri rastgele değil. None ise test p-value üretmedi (betimsel test).",
                "p_values": "Alt p-değerleri (çoklu alt-test varsa).",
                "effect_sizes": "Etki boyutu: Sapma miktarı.",
                "flags": "Ek bayraklar.",
                "z_score": "Z-skoru: Standart sapma cinsinden sapma.",
                "evidence": "Kanıt/ek detaylar.",
                "time_ms": "İşlem süresi (ms).",
                "bytes_processed": "İşlenen bayt miktarı.",
                "status": "Durum: completed (tamamlandı), skipped (atlandı), error (hata).",
                "fdr_rejected": "FDR ile reddedildi mi?",
                "fdr_q": "FDR eşiği.",
                "visuals": "Görseller (eğer varsa).",
                "reason": "Atlanma veya hata nedeni (ör. yetersiz veri).",
                "metrics": "Ek metrikler.",
            }
        },
        "en": {
            "main_title": "Pattern Analyzer Analysis Platform",
            "main_desc": "This platform offers powerful statistical tests to analyze randomness patterns in your data. Upload a file or enter data directly and get a comprehensive analysis report.",
            "results_title": "Analysis Results",
            "control_panel": "Control Panel",
            "file_tab": "File",
            "text_tab": "Text",
            "file_label": "Select File",
            "file_help": "Limit 200MB per file • BIN, TXT, DAT",
            "text_label": "Enter Data",
            "text_placeholder": "Base64 encoded data or plain text...",
            "test_selection": "Test Selection",
            "tests_label": "Tests to Run",
            "tests_help": "Select tests to run. Each test examines randomness from different angles. For example, monobit checks the balance of 0s and 1s.",
            "all_tests": "Select All Tests",
            "no_tests": "Select No Tests",
            "transform_selection": "Transform Selection",
            "transforms_label": "Transforms to Apply",
            "transforms_help": "Select transforms to apply. Transforms modify data to enhance test sensitivity, e.g., XOR to break encryption patterns.",
            "all_transforms": "Select All Transforms",
            "no_transforms": "Select No Transforms",
            "analysis_settings": "Analysis Settings",
            "fdr_label": "FDR Significance Level (q)",
            "fdr_help": "FDR (False Discovery Rate) significance level. Lower value (e.g., 0.05) means stricter testing; p-value < q fails the test.",
            "start_analysis": "Start Analysis",
            "clear": "Clear",
            "analyzing": "Analyzing...",
            "analysis_error": "Analysis error: {error}",
            "scorecard": "Scorecard",
            "findings": "Findings",
            "select_result": "Select a result",
            "selected_details": "Selected Result Details",
            "visuals": "Visuals",
            "visual_error": "Could not display visual ({name}): {error}",
            "visual_format_error": "Invalid visual format: {name}",
            "no_results": "No analysis results or empty.",
            "language": "Language",
            "failed_tests": "Failed Tests",
            "mean_effect_size": "Mean Effect Size",
            "mean_effect_size_desc": "Average effect sizes from tests (e.g., deviation measure). None if insufficient data or not calculated.",
            "p_value_distribution": "P-Value Distribution",
            "p_value_distribution_desc": "Statistics of p-values (count, mean, median, etc.). In random data, p-values should be uniformly distributed.",
            "total_tests": "Total Tests",
            "fdr_q": "FDR q",
            "skipped_tests": "Skipped Tests",
            "skipped_tests_desc": "Skipped tests: Insufficient data size or preconditions not met. Details in 'reason' column of results table.",
            "run_tests": "Run Tests",
            "test_explanations": {
                "monobit": "Monobit test: Checks the proportion of 0s and 1s. Should be approximately equal in random data.",
                "approximate_entropy": "Approximate Entropy: Measures unpredictability. Low entropy indicates regular patterns.",
                "autocorrelation": "Autocorrelation: Computes lagged correlation. High values indicate periodicity.",
                "autoencoder_anomaly": "Autoencoder Anomaly: Detects anomalies using machine learning.",
                "binary_matrix_rank": "Binary Matrix Rank: Tests for linear dependencies in matrices.",
                "block_frequency": "Block Frequency: Tests frequency distribution in blocks.",
                "classifier_labeler": "Classifier Labeler: Labels data using a classifier.",
                "conditional_entropy": "Conditional Entropy: Measures dependencies.",
                "cusum": "Cumulative Sums: Detects deviations in cumulative sums.",
                "dft_spectral_advanced": "DFT Spectral Advanced: Spectral analysis for frequency patterns.",
                "diehard_3d_spheres": "Diehard 3D Spheres: 3D sphere test (errors if data insufficient).",
                "diehard_birthday_spacings": "Diehard Birthday Spacings: Birthday spacing test.",
                "diehard_overlapping_sums": "Diehard Overlapping Sums: Overlapping sums test.",
                "dotplot": "Dotplot: Visualizes data patterns.",
                "ecb_detector": "ECB Detector: Searches for ECB mode encryption patterns.",
                "fft_spectral": "FFT Spectral: Frequency domain analysis.",
                "frequency_pattern": "Frequency Pattern: Frequency patterns and Vigenere key length estimation.",
                "hurst_exponent": "Hurst Exponent: Measures long-term dependencies.",
                "known_constants_search": "Known Constants Search: Searches for known constants.",
                "linear_complexity": "Linear Complexity: Linear complexity test.",
                "longest_run_ones": "Longest Run of Ones: Longest sequence of 1s test.",
                "lstm_gru_anomaly": "LSTM GRU Anomaly: Detects time series anomalies.",
                "lz_complexity": "LZ Complexity: Lempel-Ziv complexity.",
                "magic_detector": "Magic Detector: File type magic bytes search.",
                "maurers_universal": "Maurer's Universal: Universal statistical test.",
                "mutual_information": "Mutual Information: Mutual information measure.",
                "nist_dft_spectral": "NIST DFT Spectral: NIST spectral test.",
                "non_overlapping_template_matching": "Non-Overlapping Template: Non-overlapping template matching.",
                "overlapping_template_matching": "Overlapping Template: Overlapping template matching.",
                "blocking": "Blocking: Blocking test.",
                "quickstat": "Quickstat: Quick statistical summary.",
                "pdf_structure": "PDF Structure: PDF structure analysis.",
                "png_structure": "PNG Structure: PNG structure analysis.",
                "random_excursions": "Random Excursions: Random excursion test.",
                "random_excursions_variant": "Random Excursions Variant: Excursion variant.",
                "runs": "Runs: Runs test, checks number of changes.",
                "serial": "Serial: Serial correlation test.",
                "testu01_smallcrush": "TestU01 SmallCrush: Small crush test battery.",
                "transfer_entropy": "Transfer Entropy: Information transfer measure.",
                "zip_structure": "ZIP Structure: ZIP archive structure analysis.",
            },
            "column_explanations": {
                "test_name": "Test name",
                "passed": "Passed? (True: Randomness accepted)",
                "p_value": "P-value: Low (<0.05) means non-random. None if test doesn't produce p-value (descriptive).",
                "p_values": "Sub p-values (for multi-subtests).",
                "effect_sizes": "Effect size: Deviation measure.",
                "flags": "Additional flags.",
                "z_score": "Z-score: Deviation in standard deviations.",
                "evidence": "Evidence/extra details.",
                "time_ms": "Processing time (ms).",
                "bytes_processed": "Processed bytes.",
                "status": "Status: completed, skipped, error.",
                "fdr_rejected": "Rejected by FDR?",
                "fdr_q": "FDR threshold.",
                "visuals": "Visuals (if any).",
                "reason": "Reason for skip or error (e.g., insufficient data).",
                "metrics": "Additional metrics.",
            }
        }
    }[st.session_state.language]

    # Main content with modern header
    st.markdown(f"""
        <div style="text-align: center; padding: 2rem 0;">
            <h1 class="main-header">🔬 {lang['main_title']}</h1>
            <p class="sub-header">{lang['main_desc']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="section-header">
            <span>📊</span> {lang['results_title']}
        </div>
    """, unsafe_allow_html=True)

    # Sidebar with modern styling
    with st.sidebar:
        # Sidebar header with logo
        st.markdown("""
            <div style="text-align: center; padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1.5rem;">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🔬</div>
                <div style="font-size: 1.1rem; font-weight: 600; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Pattern Analyzer</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Language selector
        selected_lang = st.selectbox(f"🌐 {lang['language']}", options=["tr", "en"], format_func=lambda x: "🇹🇷 Türkçe" if x == "tr" else "🇬🇧 English", index=0 if st.session_state.language == "tr" else 1)
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()

        st.markdown(f"""
            <div style="font-size: 1.1rem; font-weight: 600; color: #fff; margin: 1.5rem 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span>⚙️</span> {lang['control_panel']}
            </div>
        """, unsafe_allow_html=True)
        
        # Tabs for input
        tab1, tab2 = st.tabs([f"📁 {lang['file_tab']}", f"📝 {lang['text_tab']}"])

        with tab1:
            uploaded_file = st.file_uploader(
                lang['file_label'],
                type=['bin', 'txt', 'dat'],
                help=lang['file_help']
            )

        with tab2:
            text_input = st.text_area(
                lang['text_label'],
                placeholder=lang['text_placeholder'],
                height=100
            )

        st.markdown(f"""
            <div style="font-size: 1rem; font-weight: 600; color: #fff; margin: 1.5rem 0 0.75rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span>🧪</span> {lang['test_selection']}
            </div>
        """, unsafe_allow_html=True)
        available_tests = engine.get_available_tests()
        default_tests = ["monobit", "approximate_entropy", "autocorrelation"]  # From HTML

        if 'selected_tests' not in st.session_state:
            st.session_state.selected_tests = [t for t in default_tests if t in available_tests]

        selected_tests = st.multiselect(
            lang['tests_label'],
            options=available_tests,
            default=st.session_state.selected_tests,
            help=lang['tests_help']
        )

        # Test açıklamaları için expander
        with st.expander("📖 " + ("Test Açıklamaları" if st.session_state.language == "tr" else "Test Explanations")):
            for test in available_tests:
                desc = lang['test_explanations'].get(test, "Açıklama yok." if st.session_state.language == "tr" else "No description.")
                st.markdown(f"**`{test}`**: {desc}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ {lang['all_tests']}", use_container_width=True):
                st.session_state.selected_tests = available_tests
                st.rerun()
        with col2:
            if st.button(f"❌ {lang['no_tests']}", use_container_width=True):
                st.session_state.selected_tests = []
                st.rerun()

        st.markdown(f"""
            <div style="font-size: 1rem; font-weight: 600; color: #fff; margin: 1.5rem 0 0.75rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span>🔄</span> {lang['transform_selection']}
            </div>
        """, unsafe_allow_html=True)
        available_transforms = engine.get_available_transforms()

        if 'selected_transforms' not in st.session_state:
            st.session_state.selected_transforms = []

        selected_transforms = st.multiselect(
            lang['transforms_label'],
            options=available_transforms,
            default=st.session_state.selected_transforms,
            help=lang['transforms_help']
        )

        col3, col4 = st.columns(2)
        with col3:
            if st.button(f"✅ {lang['all_transforms']}", use_container_width=True):
                st.session_state.selected_transforms = available_transforms
                st.rerun()
        with col4:
            if st.button(f"❌ {lang['no_transforms']}", use_container_width=True):
                st.session_state.selected_transforms = []
                st.rerun()

        st.markdown(f"""
            <div style="font-size: 1rem; font-weight: 600; color: #fff; margin: 1.5rem 0 0.75rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span>⚡</span> {lang['analysis_settings']}
            </div>
        """, unsafe_allow_html=True)
        fdr_q = st.slider(
            lang['fdr_label'],
            min_value=0.01,
            max_value=0.10,
            value=0.05,
            step=0.01,
            format="%.2f",
            help=lang.get('fdr_help', '')
        )

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            start_button = st.button(f"🚀 {lang['start_analysis']}", type="primary", use_container_width=True)
        with col6:
            clear_button = st.button(f"🗑️ {lang['clear']}", type="secondary", use_container_width=True)

    # Handle buttons
    if clear_button:
        st.session_state.pop('analysis_result', None)
        st.session_state.pop('selected_tests', None)
        st.session_state.pop('selected_transforms', None)
        st.rerun()

    if start_button:
        # Update session state
        st.session_state.selected_tests = selected_tests
        st.session_state.selected_transforms = selected_transforms

        # Build config
        config = {
            'data': {
                'file': uploaded_file,
                'text': text_input,
            },
            'tests': [{'name': t, 'params': {}} for t in selected_tests],
            'transforms': [{'name': tr, 'params': {}} for tr in selected_transforms],
            'fdr_q': fdr_q,
        }

        with st.spinner(lang['analyzing']):
            try:
                run_analysis(config)
            except Exception as e:
                st.error(lang['analysis_error'].format(error=str(e)))
                st.session_state['analysis_result'] = {"error": str(e)}

    # Display results if available
    if 'analysis_result' in st.session_state:
        result = st.session_state['analysis_result']
        if isinstance(result, dict) and 'error' in result:
            st.error(f"❌ {result['error']}")
        else:
            # Compute additional stats
            results = result.get('results', []) if isinstance(result, dict) else []
            total_tests = len(results)
            run_tests = sum(1 for r in results if r.get('status') != 'skipped')
            skipped_tests = total_tests - run_tests
            failed_tests = sum(1 for r in results if not r.get('passed', True) and r.get('status') != 'skipped')
            passed_tests = run_tests - failed_tests

            # Modern scorecard with cards
            scorecard = result.get('scorecard', {}) if isinstance(result, dict) else {}
            if scorecard or results:
                st.markdown(f"""
                    <div class="section-header">
                        <span>📈</span> {lang['scorecard']}
                    </div>
                """, unsafe_allow_html=True)
                
                # Modern metric cards
                cols = st.columns(5)
                with cols[0]:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value" style="color: {'#38ef7d' if failed_tests == 0 else '#ff6a00'};">{passed_tests}/{total_tests}</div>
                            <div class="metric-label">✅ {"Başarılı" if st.session_state.language == "tr" else "Passed"}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value" style="color: {'#ff6a00' if failed_tests > 0 else '#38ef7d'};">{failed_tests}</div>
                            <div class="metric-label">❌ {lang['failed_tests']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[2]:
                    effect_size_val = format_val(scorecard.get('mean_effect_size', 'N/A'))
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{effect_size_val}</div>
                            <div class="metric-label">📊 {lang['mean_effect_size']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{run_tests}</div>
                            <div class="metric-label">🔬 {lang['run_tests']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[4]:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{skipped_tests}</div>
                            <div class="metric-label">⏭️ {lang['skipped_tests']}</div>
                        </div>
                    """, unsafe_allow_html=True)

            if results:
                st.markdown(f"""
                    <div class="section-header" style="margin-top: 2rem;">
                        <span>🔍</span> {lang['findings']}
                    </div>
                """, unsafe_allow_html=True)
                
                df = pd.DataFrame(results)
                # Reindex to include all possible columns
                expected_columns = [
                    'test_name', 'passed', 'p_value', 'p_values', 'effect_sizes', 'flags',
                    'z_score', 'evidence', 'time_ms', 'bytes_processed', 'status',
                    'fdr_rejected', 'fdr_q', 'visuals', 'reason', 'metrics'
                ]
                df = df.reindex(columns=expected_columns)
                # Convert dict keys in metrics to str for Arrow compatibility
                if 'metrics' in df.columns:
                    df['metrics'] = df['metrics'].apply(lambda d: {str(k): v for k, v in d.items()} if isinstance(d, dict) else d)
                if 'p_value' in df.columns:
                    def _p_style(v):
                        try:
                            return 'background-color: rgba(238, 9, 121, 0.3); color: #ff6a00;' if float(v) < fdr_q else 'background-color: rgba(17, 153, 142, 0.2); color: #38ef7d;'
                        except Exception:
                            return ''
                    styled = df.style.map(_p_style, subset=['p_value'])
                    st.dataframe(styled, column_config={
                        col: st.column_config.TextColumn(help=lang['column_explanations'].get(col, '')) for col in expected_columns
                    }, use_container_width=True)
                else:
                    st.dataframe(df, column_config={
                        col: st.column_config.TextColumn(help=lang['column_explanations'].get(col, '')) for col in expected_columns
                    }, use_container_width=True)

                # Select a result for details
                st.markdown(f"""
                    <div class="section-header" style="margin-top: 2rem;">
                        <span>🎯</span> {lang['select_result']}
                    </div>
                """, unsafe_allow_html=True)
                option_labels = [f"{i} - {r.get('test_name', 'Unknown')}" for i, r in enumerate(results)]
                selected_label = st.selectbox("", options=option_labels, label_visibility="collapsed")
                if selected_label:
                    selected_idx = int(selected_label.split(" - ")[0])
                    selected_result = results[selected_idx]
                    
                    # Modern card for selected result
                    st.markdown(f"""
                        <div class="section-header">
                            <span>📋</span> {lang['selected_details']}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Display result in a modern card
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    st.json(selected_result)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Test-specific explanation
                    test_name = selected_result.get('test_name')
                    desc = lang['test_explanations'].get(test_name, "Açıklama yok." if st.session_state.language == "tr" else "No description.")
                    st.info(f"💡 **{'Test Açıklaması' if st.session_state.language == 'tr' else 'Test Description'}**: {desc}")

                    # If skipped or error, show reason
                    status = selected_result.get('status')
                    if status == 'skipped' or status == 'error':
                        reason = selected_result.get('reason', 'Bilinmeyen neden' if st.session_state.language == "tr" else 'Unknown reason')
                        st.warning(f"⚠️ {'Bu test' if st.session_state.language == 'tr' else 'This test'} {status} {'oldu. Neden' if st.session_state.language == 'tr' else '. Reason'}: {reason}")

                    # Visuals if any
                    visuals = selected_result.get('visuals', {})
                    if visuals:
                        st.markdown(f"""
                            <div class="section-header" style="margin-top: 1.5rem;">
                                <span>🖼️</span> {lang['visuals']}
                            </div>
                        """, unsafe_allow_html=True)
                        for vname, vdata in visuals.items():
                            if isinstance(vdata, dict):
                                if 'data_base64' in vdata:
                                    try:
                                        mime = vdata.get('mime', 'image/svg+xml')
                                        base64_data = vdata['data_base64']
                                        if mime == 'image/svg+xml':
                                            # Display SVG using markdown with modern styling
                                            st.markdown(f'''
                                                <div class="modern-card" style="text-align: center;">
                                                    <img src="data:image/svg+xml;base64,{base64_data}" alt="{vname}" style="max-width: 100%; border-radius: 8px;">
                                                    <p style="color: rgba(255,255,255,0.7); margin-top: 0.5rem;">{vname}</p>
                                                </div>
                                            ''', unsafe_allow_html=True)
                                        else:
                                            img_data = base64.b64decode(base64_data)
                                            st.image(img_data, caption=vname, use_container_width=True)
                                    except Exception as e:
                                        st.error(lang['visual_error'].format(name=vname, error=str(e)))
                                elif 'path' in vdata:
                                    try:
                                        st.image(vdata['path'], caption=vname, use_container_width=True)
                                    except Exception as e:
                                        st.error(lang['visual_error'].format(name=vname, error=str(e)))
                            else:
                                st.write(lang['visual_format_error'].format(name=vname))
            else:
                st.info(lang['no_results'])

if __name__ == "__main__":
    main()
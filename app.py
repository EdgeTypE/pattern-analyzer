import streamlit as st
import base64
import pandas as pd
import json
from patternlab.engine import Engine

st.set_page_config(page_title="PatternLab Analizi", layout="wide", page_icon="🔬")

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
        st.session_state.language = "tr"

    lang = {
        "tr": {
            "main_title": "🔬 PatternLab Analiz Platformu",
            "main_desc": "Bu platform, verilerinizde rastgelelik paternlerini analiz etmek için güçlü istatistiksel testler sunar. Dosya yükleyin veya doğrudan veri girin ve kapsamlı bir analiz raporu elde edin.",
            "results_title": "📊 Analiz Sonuçları",
            "control_panel": "⚙️ Kontrol Paneli",
            "file_tab": "📁 Dosya",
            "text_tab": "✏️ Metin",
            "file_label": "Dosya Seçin",
            "file_help": "Limit 200MB per file • BIN, TXT, DAT",
            "text_label": "Veri Girin",
            "text_placeholder": "Base64 encoded data veya doğrudan metin girin...",
            "test_selection": "🧪 Test Seçimi",
            "tests_label": "Çalıştırılacak Testler",
            "tests_help": "Çalıştırılacak testleri seçin. Her test, verinin rastgeleliğini farklı açılardan inceler. Örneğin, monobit testi 0 ve 1'lerin dağılımını kontrol eder.",
            "all_tests": "Tüm Testleri Seç",
            "no_tests": "Hiçbir Test Seçme",
            "transform_selection": "🔄 Transform Seçimi",
            "transforms_label": "Uygulanacak Transformlar",
            "transforms_help": "Uygulanacak transformları seçin. Transformlar, veriyi dönüştürerek testlerin hassasiyetini artırabilir, örneğin XOR ile şifreleme paternlerini kırar.",
            "all_transforms": "Tüm Transformları Seç",
            "no_transforms": "Hiçbir Transform Seçme",
            "analysis_settings": "⚙️ Analiz Ayarları",
            "fdr_label": "FDR Anlamlılık Düzeyi (q)",
            "fdr_help": "FDR (False Discovery Rate) anlamlılık düzeyi. Düşük değer (ör. 0.05) daha katı test anlamına gelir; p-value < q ise test başarısız sayılır.",
            "start_analysis": "🚀 Analizi Başlat",
            "clear": "🗑️ Temizle",
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
                # Diğer testler için benzer açıklamalar ekleyin...
                # (Tüm testler için eklemek ideal, ama örnek olarak birkaç tane)
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
            # İngilizce karşılıklarını ekleyin...
            "main_title": "🔬 PatternLab Analysis Platform",
            # ... diğerleri
            "test_explanations": {
                "monobit": "Monobit test: Checks the proportion of 0s and 1s. Should be approximately equal in random data.",
                # ... diğerleri
            },
            "column_explanations": {
                "test_name": "Test name",
                "passed": "Passed? (True: Randomness accepted)",
                "p_value": "P-value: Low (<0.05) means non-random. None if test doesn't produce p-value (descriptive).",
                # ... diğerleri
            }
        }
    }[st.session_state.language]

    # Main content
    st.markdown(f"""
        <h1 id="pattern-lab-analiz-platformu">{lang['main_title']}</h1>
    """, unsafe_allow_html=True)
    st.write(lang['main_desc'])
    st.markdown(f"""
        <h2 id="analiz-sonuclari">{lang['results_title']}</h2>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        # Language selector
        selected_lang = st.selectbox(lang['language'], options=["tr", "en"], format_func=lambda x: "Türkçe" if x == "tr" else "English", index=0 if st.session_state.language == "tr" else 1)
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()

        st.header(lang['control_panel'])
        st.divider()

        # Tabs for input
        tab1, tab2 = st.tabs([lang['file_tab'], lang['text_tab']])

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

        st.subheader(lang['test_selection'])
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
        with st.expander("Test Açıklamaları"):
            for test in available_tests:
                desc = lang['test_explanations'].get(test, "Açıklama yok.")
                st.write(f"**{test}**: {desc}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(lang['all_tests']):
                st.session_state.selected_tests = available_tests
                st.rerun()
        with col2:
            if st.button(lang['no_tests']):
                st.session_state.selected_tests = []
                st.rerun()

        st.subheader(lang['transform_selection'])
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
            if st.button(lang['all_transforms']):
                st.session_state.selected_transforms = available_transforms
                st.rerun()
        with col4:
            if st.button(lang['no_transforms']):
                st.session_state.selected_transforms = []
                st.rerun()

        st.subheader(lang['analysis_settings'])
        fdr_q = st.slider(
            lang['fdr_label'],
            min_value=0.01,
            max_value=0.10,
            value=0.05,
            step=0.01,
            format="%.2f",
            help=lang.get('fdr_help', '')
        )

        col5, col6 = st.columns(2)
        with col5:
            start_button = st.button(lang['start_analysis'], type="primary")
        with col6:
            clear_button = st.button(lang['clear'], type="secondary")

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
            st.error(result['error'])
        else:
            # Compute additional stats
            results = result.get('results', []) if isinstance(result, dict) else []
            total_tests = len(results)
            run_tests = sum(1 for r in results if r.get('status') != 'skipped')
            skipped_tests = total_tests - run_tests
            failed_tests = sum(1 for r in results if not r.get('passed', True) and r.get('status') != 'skipped')

            # scorecard'ı st.metric ile göster
            scorecard = result.get('scorecard', {}) if isinstance(result, dict) else {}
            if scorecard:
                st.subheader(lang['scorecard'])
                # Custom metrics
                cols = st.columns(5)
                cols[0].metric(lang['failed_tests'], f"{failed_tests} / {total_tests}")
                cols[1].metric(lang['mean_effect_size'], format_val(scorecard.get('mean_effect_size', 'None')), help=lang.get('mean_effect_size_desc', ''))
                cols[2].metric(lang['p_value_distribution'], format_val(scorecard.get('p_value_distribution', {}), max_len=40), help=lang.get('p_value_distribution_desc', ''))
                cols[3].metric(lang['run_tests'], run_tests)
                cols[4].metric(lang['skipped_tests'], skipped_tests, help=lang.get('skipped_tests_desc', ''))

            if results:
                st.subheader(lang['findings'])
                df = pd.DataFrame(results)
                # Reindex to include all possible columns
                expected_columns = [
                    'test_name', 'passed', 'p_value', 'p_values', 'effect_sizes', 'flags',
                    'z_score', 'evidence', 'time_ms', 'bytes_processed', 'status',
                    'fdr_rejected', 'fdr_q', 'visuals', 'reason', 'metrics'
                ]
                df = df.reindex(columns=expected_columns)
                # Do not stringify metrics, let dataframe handle
                if 'p_value' in df.columns:
                    def _p_style(v):
                        try:
                            return 'background-color: red' if float(v) < fdr_q else ''
                        except Exception:
                            return ''
                    styled = df.style.applymap(_p_style, subset=['p_value'])
                    st.dataframe(styled, column_config={
                        col: st.column_config.TextColumn(help=lang['column_explanations'].get(col, '')) for col in expected_columns
                    })
                else:
                    st.dataframe(df, column_config={
                        col: st.column_config.TextColumn(help=lang['column_explanations'].get(col, '')) for col in expected_columns
                    })

                # Select a result for details
                option_labels = [f"{i} - {r.get('test_name', 'Unknown')}" for i, r in enumerate(results)]
                selected_label = st.selectbox(lang['select_result'], options=option_labels)
                if selected_label:
                    selected_idx = int(selected_label.split(" - ")[0])
                    selected_result = results[selected_idx]
                    st.subheader(lang['selected_details'])
                    st.json(selected_result)

                    # Test-specific explanation
                    test_name = selected_result.get('test_name')
                    desc = lang['test_explanations'].get(test_name, "Açıklama yok.")
                    st.write(f"**Test Açıklaması**: {desc}")

                    # If skipped or error, show reason
                    status = selected_result.get('status')
                    if status == 'skipped' or status == 'error':
                        reason = selected_result.get('reason', 'Bilinmeyen neden')
                        st.warning(f"Bu test {status} oldu. Neden: {reason}")

                    # Visuals if any
                    visuals = selected_result.get('visuals', {})
                    if visuals:
                        st.subheader(lang['visuals'])
                        for vname, vdata in visuals.items():
                            if isinstance(vdata, dict):
                                if 'data_base64' in vdata:
                                    try:
                                        mime = vdata.get('mime', 'image/svg+xml')
                                        img_data = base64.b64decode(vdata['data_base64'])
                                        st.image(img_data, caption=vname, use_column_width=True)
                                    except Exception as e:
                                        st.error(lang['visual_error'].format(name=vname, error=str(e)))
                                elif 'path' in vdata:
                                    try:
                                        st.image(vdata['path'], caption=vname, use_column_width=True)
                                    except Exception as e:
                                        st.error(lang['visual_error'].format(name=vname, error=str(e)))
                            else:
                                st.write(lang['visual_format_error'].format(name=vname))
            else:
                st.info(lang['no_results'])

if __name__ == "__main__":
    main()
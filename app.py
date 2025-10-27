import streamlit as st
import threading
from patternlab.engine import Engine
import pandas as pd

st.set_page_config(page_title="PatternLab Analizi", layout="wide")

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
            input_bytes = text.encode('utf-8')

    # engine.analyze çağrısı doğru parametrelerle
    result = engine.analyze(input_bytes, config)
    st.session_state['analysis_result'] = result

def main():
    st.title("Pattern Analyzer")
    st.write("Bu, temel Streamlit uygulamasıdır.")

    # Sidebar control panel
    st.sidebar.header("Kontrol Paneli")

    uploaded_file = st.sidebar.file_uploader(
        "Dosya Yükle", accept_multiple_files=False, type=['bin', 'txt']
    )

    text_input = st.sidebar.text_area(
        "Veri (Base64 veya metin)",
        placeholder='Base64 encoded data or plain text',
        height=150,
    )

    # Use engine to populate available tests/transforms; default select all
    available_tests = engine.get_available_tests()
    available_transforms = engine.get_available_transforms()

    selected_tests = st.sidebar.multiselect(
        "Testler",
        options=available_tests,
        default=available_tests,
    )

    selected_transforms = st.sidebar.multiselect(
        "Transformlar",
        options=available_transforms,
        default=available_transforms,
    )

    analizi_baslat = st.sidebar.button("Analizi Başlat")

    # Persist current UI values into session_state so we can build config from it
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = uploaded_file
    if 'text_input' not in st.session_state:
        st.session_state.text_input = text_input
    if 'selected_tests' not in st.session_state:
        st.session_state.selected_tests = selected_tests
    if 'selected_transforms' not in st.session_state:
        st.session_state.selected_transforms = selected_transforms

    if analizi_baslat:
        # Update session_state with latest values
        st.session_state.uploaded_file = uploaded_file
        st.session_state.text_input = text_input
        st.session_state.selected_tests = selected_tests
        st.session_state.selected_transforms = selected_transforms

        # Build config from session_state
        config = {
            'data': {
                'file': st.session_state.uploaded_file,
                'text': st.session_state.text_input,
            },
            'tests': [{'name': t} for t in st.session_state.selected_tests],
            'transforms': [{'name': tr} for tr in st.session_state.selected_transforms],
        }

        with st.spinner('Analiz yapılıyor...'):
            # Thread yerine direkt çağrı yapalım
            try:
                run_analysis(config)
            except Exception as e:
                st.error(f"Analiz hatası: {str(e)}")
                st.session_state['analysis_result'] = {"error": str(e)}

    # Gösterim: Analiz sonucu session_state'te varsa ana ekranda göster
    if 'analysis_result' in st.session_state:
        st.header("Analiz Sonuçları")
        result = st.session_state['analysis_result']

        # scorecard'ı st.metric ile göster
        scorecard = result.get('scorecard', {}) if isinstance(result, dict) else {}
        if scorecard:
            st.subheader("Scorecard")
            keys = list(scorecard.keys())
            if keys:
                cols = st.columns(len(keys))
                for i, k in enumerate(keys):
                    try:
                        val = scorecard[k]
                    except Exception:
                        val = str(scorecard.get(k))
                    cols[i].metric(str(k), str(val))

        # results listesini dataframe içinde göster, p-value'a göre renklendirme
        results = result.get('results', []) if isinstance(result, dict) else []
        st.subheader("Bulgular")
        if results:
            df = pd.DataFrame(results)
            # Metrics sütunu sorun çıkarabilir, onu çıkaralım
            if 'metrics' in df.columns:
                df = df.drop(columns=['metrics'])
            if 'p_value' in df.columns:
                def _p_style(v):
                    try:
                        return 'background-color: red' if float(v) < 0.05 else ''
                    except Exception:
                        return ''
                styled = df.style.map(_p_style, subset=['p_value'])
                st.dataframe(styled)
            else:
                st.dataframe(df)

            # Kullanıcının bir sonucu seçebilmesi için selectbox (tablodan tıklama benzeri)
            option_labels = []
            for idx, row in df.iterrows():
                name = row.get('name') if 'name' in row else None
                label = f"{idx}"
                if name:
                    label = f"{idx} - {name}"
                option_labels.append(label)

            selected_label = st.selectbox("Bir sonuç seçin", options=option_labels)
            if selected_label is not None and selected_label != "":
                selected_idx = int(str(selected_label).split(" - ")[0])
                selected_result = results[selected_idx]
                st.subheader("Seçilen Sonucun Detayları")
                st.json(selected_result)

                # Eğer seçilen sonucun görselleri varsa göster (SVG/PNG)
                visuals = selected_result.get('visuals') if isinstance(selected_result, dict) else None
                if visuals:
                    st.subheader("Görseller")
                    for vname, vdata in visuals.items():
                        if isinstance(vdata, dict):
                            if 'data_base64' in vdata:
                                try:
                                    import base64
                                    mime = vdata.get('mime', 'image/svg+xml')
                                    img_data = base64.b64decode(vdata['data_base64'])
                                    st.image(img_data, caption=vname, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Görsel gösterilemedi ({vname}): {str(e)}")
                            elif 'path' in vdata:
                                try:
                                    st.image(vdata['path'], caption=vname, use_column_width=True)
                                except Exception as e:
                                    st.error(f"Görsel gösterilemedi ({vname}): {str(e)}")
                            else:
                                st.write(f"Görsel verisi tanınmıyor: {vname}")
                        else:
                            st.write(f"Görsel formatı yanlış: {vname}")
        else:
            st.info("Henüz analiz sonucu yok veya sonuç listesi boş.")

if __name__ == "__main__":
    main()
# main.py
import streamlit as st

from ingestion import ingest_file
from qa import answer_question

st.set_page_config(page_title="Belge Analiz ve Soru-Cevap", layout="centered")
st.title("Belge Analiz ve Soru-Cevap Sistemi")

# --- Oturum durumu ---
if "indexed" not in st.session_state:
    st.session_state["indexed"] = False
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- ÜST BÖLÜM: Dosya yükleme ---
uploaded_file = st.file_uploader(
    "Belge seçin (PDF, JPG, PNG)",
    type=["pdf", "jpg", "jpeg", "png"],
)

if uploaded_file is not None:
    if st.button("Yükle ve İndeksle"):
        with st.spinner("Belge işleniyor, lütfen bekleyin..."):
            try:
                chunk_count = ingest_file(uploaded_file)
                st.session_state["indexed"] = True
                st.session_state["messages"] = []  # yeni belge -> geçmişi sıfırla
                st.success(
                    f"Belge indekslendi ({chunk_count} parça). "
                    "Artık soru sorabilirsiniz."
                )
            except ValueError as e:
                st.session_state["indexed"] = False
                st.error(str(e))

st.divider()

# --- ALT BÖLÜM: Chat ---
if not st.session_state["indexed"]:
    st.info("Soru sorabilmek için önce bir belge yükleyip indeksleyin.")
else:
    # Önceki mesajları göster
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Yeni soru
    if question := st.chat_input("Belge hakkında soru sorun"):
        # Kullanıcı mesajı
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        # Yanıt üret
        with st.chat_message("assistant"):
            with st.spinner("Yanıt hazırlanıyor..."):
                answer = answer_question(question)
            st.write(answer)

        st.session_state["messages"].append(
            {"role": "assistant", "content": answer}
        )

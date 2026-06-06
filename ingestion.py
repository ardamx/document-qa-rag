# ingestion.py
import os
import tempfile

from ocr import extract_from_pdf, extract_from_image
from embeddings import chunk_text
from vectorstore import reset_collection, add_chunks

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def _extract_text(uploaded_file) -> str:
    """
    Yüklenen dosyayı doğrular, geçici diske yazar ve tipine göre
    doğru extraction yöntemine yönlendirir.
    """
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Desteklenmeyen dosya formatı: {ext}")

    # Streamlit'ten gelen dosyayı geçici diske yaz
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        if ext == ".pdf":
            return extract_from_pdf(tmp_path)
        else:
            return extract_from_image(tmp_path)
    finally:
        # Geçici dosyayı temizle
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def ingest_file(uploaded_file) -> int:
    """
    Tam ingestion akışı:
    1. Metni çıkar (OCR / PyMuPDF)
    2. Önceki belgeyi temizle (reset)
    3. Chunk'lara böl
    4. Vektör veritabanına ekle

    Dönen değer: indekslenen chunk sayısı
    """
    text = _extract_text(uploaded_file)

    if not text.strip():
        raise ValueError("Belgeden metin çıkarılamadı.")

    reset_collection()
    chunks = chunk_text(text)
    add_chunks(chunks)

    return len(chunks)

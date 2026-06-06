# ocr.py
import io

import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image

# EasyOCR reader'ı bir kez başlat (TR + EN)
# gpu=True ise CUDA yoksa otomatik CPU'ya düşer
reader = easyocr.Reader(["tr", "en"], gpu=True)

CHAR_THRESHOLD = 10  # bu sayının altındaki sayfa taranmış kabul edilir


def _ocr_image(image: np.ndarray) -> str:
    """Bir numpy görüntüsünden metin çıkarır."""
    result = reader.readtext(image, detail=0)
    return " ".join(result)


def _ocr_page_images(page, doc) -> str:
    """Bir sayfadaki gömülü görüntüleri OCR'dan geçirir."""
    texts = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
            ocr_text = _ocr_image(img)
            if ocr_text.strip():
                texts.append(ocr_text)
        except Exception:
            continue
    return (" " + " ".join(texts)) if texts else ""


def extract_from_image(image_path: str) -> str:
    """JPG/PNG dosyasından metin çıkarır."""
    img = np.array(Image.open(image_path).convert("RGB"))
    return _ocr_image(img)


def extract_from_pdf(pdf_path: str) -> str:
    """
    PDF'ten metin çıkarır.
    - Sayfa metni < CHAR_THRESHOLD ise: tüm sayfayı OCR'a gönderir
    - Aksi halde: PyMuPDF metnini alır + image block'ları OCR'a gönderir
    """
    doc = fitz.open(pdf_path)
    full_text = []

    for page in doc:
        text = page.get_text()

        if len(text.strip()) < CHAR_THRESHOLD:
            # Muhtemelen taranmış sayfa -> tüm sayfayı render et, OCR'a gönder
            pix = page.get_pixmap()
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:  # RGBA gelirse RGB'ye indir
                img = img[:, :, :3]
            page_text = _ocr_image(img)
        else:
            # Metin tabanlı sayfa -> PyMuPDF metni + varsa gömülü görüntüler
            page_text = text + _ocr_page_images(page, doc)

        full_text.append(page_text)

    doc.close()
    return "\n\n".join(full_text)

# Belge Analiz ve Soru-Cevap Sistemi

Kullanıcıların PDF ve görüntü (JPG, PNG) formatındaki belgeleri yükleyip
bu belgeler hakkında doğal dilde soru sorabildiği, yapay zeka destekli bir
belge analiz sistemi. Sistem tamamen local çalışır ve herhangi bir dış
API anahtarı gerektirmez.

## Özellikler

- PDF ve görüntü (JPG, PNG) belge yükleme
- Türkçe ve İngilizce metin tanıma (OCR)
- Belge içeriğine dayalı soru-cevap
- Belgede olmayan bilgiler için hallucination kontrolü
- Streamlit tabanlı web arayüzü

## Mimari

```
Ingestion → Extraction → Indexing → Retrieval + Generation → UI
```

| Katman    | Teknoloji                                  |
|-----------|--------------------------------------------|
| PDF metin | PyMuPDF                                    |
| OCR       | EasyOCR (TR + EN)                          |
| Embedding | sentence-transformers (multilingual-mpnet) |
| Vector DB | ChromaDB                                   |
| LLM       | gemma3:12b-it-q4_K_M (Ollama)              |
| Arayüz    | Streamlit                                  |

## Gereksinimler

- Docker ve Docker Compose
- GPU kullanımı için **NVIDIA Container Toolkit** (önerilir)

> **Not:** GPU önerilir. NVIDIA Container Toolkit kurulu değilse sistem
> CPU üzerinde çalışır, ancak LLM yanıt süreleri uzar.

## Kurulum ve Çalıştırma

```bash
docker compose up
```

İlk açılışta LLM modeli (~7 GB) otomatik indirilir, bu işlem birkaç
dakika sürebilir. Sonraki açılışlarda model yeniden indirilmez.

Sistem hazır olduğunda tarayıcıdan açın:

```
http://localhost:8501
```

## Kullanım

1. Üst bölümden bir belge seçin (PDF, JPG veya PNG).
2. "Yükle ve İndeksle" butonuna basın ve indekslemenin tamamlanmasını
   bekleyin.
3. Alt bölümdeki sohbet alanından belge hakkında soru sorun.

Yeni bir belge yüklendiğinde önceki belgeye ait veriler temizlenir.

## Yapılandırma

Varsayılan model `docker-compose.yml` içindeki ortam değişkeninden
değiştirilebilir:

```yaml
environment:
  - OLLAMA_MODEL=gemma3:12b-it-q4_K_M
```

GPU'su olmayan veya sınırlı kaynağa sahip makinelerde daha küçük bir
model (örneğin `gemma3:4b-it-q4_K_M`) tercih edilebilir.

## Proje Yapısı

```
.
├── main.py          Streamlit arayüzü
├── ingestion.py     Dosya doğrulama ve yönlendirme
├── ocr.py           PyMuPDF + EasyOCR metin çıkarımı
├── embeddings.py    Chunking ve embedding
├── vectorstore.py   ChromaDB vektör saklama/sorgulama
└── qa.py            Retrieval + LLM yanıt üretimi
```

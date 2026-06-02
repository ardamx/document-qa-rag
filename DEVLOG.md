# DEVLOG.md

## 02 Haziran 2026

### Mimari Kararlar

Case study gereksinimlerini özetleyecek olursak:

- PDF ve görüntü desteği: extraction katmanı gerekmektedir.
- Türkçe + İngilizce: dil-agnostik OCR ve embedding model gerekmektedir.
- Hallucination: Hallucination önleme için retrieval aşamasında similarity threshold
  (düşük eşleşmeli sorgular LLM'e gönderilmeden reddedilir), generation aşamasında system-prompt guardrail (LLM yalnızca verilen bağlamı kullanmakla kısıtlanır)
  kullanılmasına karar verildi.
- Başkaları tarafından kolayca çalıştırılabilir: sıfır dış API bağımlılığı, tek komutla ayağa kalkan sistem

Bu gereksinimlere göre local çalışan,
Docker ile konteynerize edilmiş bir RAG pipeline geliştirilecektir.

---

### LLM Seçimi

Yüksek lisans tezimde (LLM-Enabled Make-or-Buy Decision Support System)
altı model beş kriter üzerinden karşılaştırılmıştır:
M/B Decision Consistency, Evidence Interpretation Accuracy,
Polarity Inversion Count, Hallucination Rate, Completeness & Clarity.
Her kriter 0–2 puan, beş ayrı case, toplam 50 puan üzerinden:

| Model                  | Toplam Skor |
|------------------------|-------------|
| Gemma 3 27B            | 47          |
| Qwen 3 32B             | 45          |
| Mistral Small 3.2 24B  | 44          |
| Phi-4 14B              | 40          |
| Qwen 3 14B             | 39          |
| Qwen 3 8B              | 32          |
| Llama 3.1 8B           | 28          |

Kalite açısından Gemma 3 27B öne çıkmaktadır ama 27B modeli
local çalıştırmak yüksek VRAM gerektirecektir ve "kolayca çalıştırılabilir"
kriterini karşılamayacaktır.

Bu trade-off'u çözmek için Gemma 3 modellerinden `gemma3:12b-it-q4_K_M` varyantı seçilmiştir.

- **12B:** 27B'ye kıyasla kabul edilebilir kalite kaybıyla çok daha
  düşük VRAM gereksinimi
- **-it (instruction-tuned):** Hallucination kontrolü için talimatları takip etme kapasitesi
- **q4_K_M:** Aynı parametre sayısında daha düşük boyut

---

### OCR Seçimi

Open-source OCR seçimi için gerçekleştirilen internet araştırması sonucunda
ulaşılan Choudhary et al. (2025) çalışması, Tesseract, EasyOCR ve PaddleOCR’ı
karşılaştırmalı olarak değerlendirmiştir. EasyOCR Tesseract'a kıyasla belirgin
biçimde üstünlük göstermektedir (CER: %4.12 vs %8.73). Özellikle fotoğrafla çekilmiş
ve düşük kaliteli belgelerde bu fark daha da açılmaktadır. Çalışma EasyOCR'ı
"hız ve doğruluk dengesi mükemmel, Python API'si sade" olarak tanımlayıp genel amaçlı
uygulamalar için önermekte olup bu proje kapsamında da EasyOCR seçilmiştir.

---

### PDF İşleme Stratejisi

PDF'ler heterojen olabilmektedir. Bazı sayfalar seçilebilir metin içerirken
bazıları taranmış görüntüden oluşmakta, bazıları karışık olabilmektedir.

Tasarlanan strateji:

- Sayfa başına karakter sayısı < 10 ise sayfa büyük olasılıkla
  taranmış -> tüm sayfayı EasyOCR'a gönder
- ≥ 10 ise PyMuPDF ile metin bloklarını çıkar, image block'ları
  ayrıca EasyOCR'a gönder ve metne ekle

Bu yaklaşım metin kaybını önlemekte ve gereksiz OCR çağrısını minimize
etmektedir.

---

### Mimari

Mimari, belgeyi işlenebilir metne
dönüştüren extraction katmanı ve kullanıcı sorularını yanıtlayan RAG
katmanı etrafında tasarlanmıştır.

Ingestion → Extraction → Indexing → RAG → UI

| Katman                  | Seçim                                      | Gerekçe                                              |
|-------------------------|--------------------------------------------|------------------------------------------------------|
| PDF metin               | PyMuPDF                                    | Hızlı, güvenilir                                     |
| OCR                     | EasyOCR (TR+EN, GPU)                       | Yukarıda açıklandı                                   |
| Embedding               | sentence-transformers (multilingual-mpnet) | Türkçe+İngilizce, tamamen local                      |
| Vector DB               | ChromaDB                                   | Local persistence, RAG için yeterli, kurulum minimal |
| LLM                     | gemma3:12b-it-q4_K_M (Ollama)              | Yukarıda açıklandı                                   |
| UI                      | Streamlit                                  | Hızlı prototipleme, tek dosya                        |
| Infra                   | Docker Compose                             | Sıfır dış bağımlılık, tek komutla çalışır            |

Modül yapısı:
```
app/
├── main.py          ← Streamlit UI
├── ingestion.py     ← dosya tespiti, yönlendirme
├── ocr.py           ← PyMuPDF + EasyOCR
├── embeddings.py    ← sentence-transformers
├── vectorstore.py   ← ChromaDB
└── qa.py            ← Ollama + prompt + similarity threshold
```


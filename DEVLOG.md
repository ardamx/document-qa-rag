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
altı modeli beş kriter üzerinden karşılaştırdım:
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

Kalite açısından Gemma 3 27B açık ara öne çıktı. Ancak 27B modeli
local çalıştırmak yüksek VRAM gerektirir ve "kolayca çalıştırılabilir"
kriterini karşılamaz.

Bu trade-off'u çözmek için Gemma ailesinin daha küçük varyantlarını
değerlendirdim. `gemma3:12b-it-q4_K_M` seçimimin gerekçesi:

- **12B:** 27B'ye kıyasla kabul edilebilir kalite kaybıyla çok daha
  düşük VRAM gereksinimi
- **-it (instruction-tuned):** "Yalnızca bağlamdaki bilgiyi kullan"
  gibi talimatları takip etme kapasitesi; hallucination kontrolü için
  kritik
- **q4_K_M:** K-means quantization, aynı bit sayısında standart Q4'e
  göre daha iyi kalite koruması sağlıyor

---

### OCR Seçimi

Pragmile'ın Nisan 2025 benchmark'ını ([kaynak](https://pragmile.com/ocr-ranking-2025-comparison-of-the-best-text-recognition-and-document-structure-software/))
referans aldım. Sekiz araç karşılaştırılmış, genel sıralama:

| Araç                      | Final Skor |
|---------------------------|------------|
| ABBYY FlexiCapture        | 8.8 / 10   |
| PaddleOCR + PP-Structure  | 8.3 / 10   |
| Amazon Textract           | 8.0 / 10   |
| Adobe PDF Extract API     | 8.0 / 10   |
| Google Document AI        | 8.0 / 10   |
| Azure Form Recognizer     | 7.2 / 10   |
| DocTR                     | 5.7 / 10   |
| Tesseract + Layout Parser | 5.5 / 10   |

Benchmark tablo/form çıkarma ağırlıklı bir değerlendirme. Benim
önceliklerim farklı: düz metin çıkarma kalitesi, Türkçe desteği ve
kurulum kolaylığı. Tablo çıkarma bu projenin gereksinimi değil.

Bu perspektiften değerlendirince:

- **ABBYY:** Ticari lisans, local deployment karmaşık → elendu
- **PaddleOCR + PP-Structure:** En iyi open-source skor, ancak
  PaddlePaddle bağımlılığı kurulum sorunlarıyla biliniyor ve asıl
  gücü tablo analizinde — benim için over-engineering
- **Tesseract:** Türkçe kalitesi benchmark'ta 7/10, yetersiz

Benchmark'ta yer almayan **EasyOCR**'ı ayrıca değerlendirdim:
PyTorch tabanlı, Türkçe dahil 80+ dil desteği, `pip install easyocr`
ile kurulum tamamlanıyor, GPU ile hızlanıyor. Düz metin + Türkçe +
kolay kurulum kriterlerini en iyi karşılayan seçenek bu.

Üretim ortamında Türkçe tablo içeren belgeler yoğunsa PaddleOCR'a
geçiş öneririm.

---

### PDF İşleme Stratejisi

PDF'ler heterojen olabiliyor: bazı sayfalar seçilebilir metin içerirken
bazıları taranmış görüntüden oluşuyor, bazıları ikisini birden barındırıyor.

Tasarladığım strateji:

- Sayfa başına karakter sayısı < 10 ise sayfa büyük olasılıkla
  taranmış → tüm sayfa EasyOCR'a gönder
- ≥ 10 ise PyMuPDF ile metin bloklarını çıkar; image block'ları
  ayrıca EasyOCR'a gönder ve metne ekle

Bu yaklaşım metin kaybını önlüyor ve gereksiz OCR çağrısını minimize
ediyor.

---

### Mimari

Ingestion → Extraction → Indexing → Retrieval + Generation → UI

| Katman                  | Seçim                                      | Gerekçe                                              |
|-------------------------|--------------------------------------------|------------------------------------------------------|
| PDF metin               | PyMuPDF                                    | Hızlı, güvenilir, text layer tespiti için yeterli    |
| OCR                     | EasyOCR (TR+EN, GPU)                       | Yukarıda açıklandı                                   |
| Embedding               | sentence-transformers (multilingual-mpnet) | Türkçe+İngilizce, tamamen local                      |
| Vector DB               | ChromaDB                                   | Local persistence, RAG için yeterli, kurulum minimal |
| LLM                     | gemma3:12b-it-q4_K_M (Ollama)              | Yukarıda açıklandı                                   |
| UI                      | Streamlit                                  | Hızlı prototipleme, tek dosya                        |
| Infra                   | Docker Compose                             | Sıfır dış bağımlılık, tek komutla çalışır            |

Servis sayısını minimumda tuttum: Ollama ve Streamlit app. ChromaDB
ve sentence-transformers uygulama içinde çalışıyor, ayrı container
gerektirmemektedir.

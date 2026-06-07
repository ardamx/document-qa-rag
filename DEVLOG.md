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
.
├── main.py          ← Streamlit UI
├── ingestion.py     ← dosya tespiti, yönlendirme
├── ocr.py           ← PyMuPDF + EasyOCR
├── embeddings.py    ← sentence-transformers
├── vectorstore.py   ← ChromaDB
└── qa.py            ← Ollama + prompt + similarity threshold
```

---

## 05 Haziran 2026

### GPU ve Container Kararı

Case study'nin herkes tarafından kolayca çalıştırılabilir isterini karşılayabilmek
için Ollama ve EasyOCR servislerinin container içerisine alınmasına karar verilmiştir.
Fakat container içerisinden GPU'ya erişebilmek için sistemin çalıştırılacağı makinada
NVIDIA Container Toolkit yüklü olması ihtiyacı ortaya çıkmaktadır.
Her iki servis de toolkit kurulu değilse otomatik olarak CPU'ya düşmektedir.
CPU'da gemma3:12b performansı yavaşlamaktadır (tahmini 2-5 dk/cevap).
README'ye "GPU önerilir, yoksa performans düşer" notu eklenmiştir.

### UI Tasarımı

UI için GPT tarzı tek ekran yerine iki bölümlü yapı tercih edilmiştir:
üstte dosya yükleme, altta chat box. Chat alanı indexing tamamlanana
kadar disabled kalmaktadır. Böylece iki aşama (önce belge hazırlama,
sonra sorgulama) net ayrılmakta ve kullanıcının boş veritabanına soru
sorması engellenmektedir.

Chat geçmişi `session_state`'te tutulup ekranda gösterilmekte, ancak
prompt'a dahil edilmemektedir. Her soru, retrieve edilen chunk'larla
bağımsız olarak yanıtlanmaktadır. Önceki soruların prompt'a katılması
context'i şişirip hallucination riskini artıracağından tercih
edilmemiştir; case çok turlu konuşma değil, belge üzerinden soru-cevap
gerektirmektedir.

### Indexing Katmanı (embedding + vector store)

Embedding modeli olarak Türkçe ve İngilizce destekleyen, local çalışan
`paraphrase-multilingual-mpnet-base-v2` seçilmiştir. Model lazy loading
ile ilk kullanımda yüklenmektedir.

Chunk boyutu 300 kelime, örtüşme 50 kelime olarak belirlenmiştir. Boyut seçimi
embedding modelinin 512 token sınırı ve LLamaIndex benchmark raporuna göre belirlenmiştir.
(https://www.llamaindex.ai/blog/evaluating-the-ideal-chunk-size-for-a-rag-system-using-llamaindex-6207e5d3fec5)

Vektör veritabanı olarak ChromaDB `PersistentClient` kullanılmıştır;
veriler Docker volume ile kalıcıdır. `reset_collection`, yeni belge
yüklendiğinde önceki chunk'ları silerek belge karışmasını önlemektedir.

`query` fonksiyonu chunk'larla birlikte benzerlik mesafesini de
döndürmektedir. Bu mesafe qa katmanında similarity threshold için
kullanılacak, yeterince eşleşmeyen sorular LLM'e gönderilmeden
reddedilecektir.

---

## 06 Haziran 2026

### Context Window (num_ctx)

`num_ctx` 4096 olarak ayarlanmıştır. Varsayılan 2048, system prompt +
üç chunk + soru toplamını zorlayıp bağlamı kırpabileceği anlaşılmıştır.

### Retrieval + Generation Katmanı (qa)

Başta belirlenmiş olan iki aşamalı hallucination kontrolü için retrieval tarafında
soru-belge benzerliği `DISTANCE_THRESHOLD` ile kontrol edilmiştir.
Generation tarafında ise system prompt'a kurallar eklenmiştir ve `temperature` değeri düşük tutulmuştur.
`DISTANCE_THRESHOLD` ve `temperature` için nihai değerler test aşamasında belirlenecektir.

### Model Yükleme (entrypoint)

Ollama servisi ayağa kalktığında model otomatik inmediği için bir
`entrypoint.sh` scripti eklenmiştir. Script Ollama sunucusunu başlatmakta,
hazır olmasını bekledikten sonra modeli çekmektedir.

### Retrieval Kalibrasyonu (cosine geçişi)

İlk testlerde ChromaDB'nin varsayılan squared L2 mesafesiyle alakalı ve
alakasız soruların değer aralıkları (~9-10 ve ~14-15) birbirine fazla
yakın çıktı, güvenilir bir eşik belirlenemedi.

Bu nedenle vektör veritabanı kosinüs mesafesine (`hnsw:space: cosine`)
geçirildi; değerler 0-2 aralığında normalize olduğu için alakalı/alakasız
ayrımı belirginleşti.

Ayrıca belge slayt formatında kısa maddelerden oluştuğu için chunk boyutu
200 kelime / 40 örtüşme olarak düşürüldü ve `N_RESULTS` 3'ten 5'e
çıkarıldı. Tekil geçişli terimlerin retrieval'da geride kaldığı
gözlemlendiğinden bu artış recall'u iyileştirdi.

Kalibrasyon sonrası gözlemlenen mesafeler: belgede bulunan sorular
0.67-0.78, bulunmayan sorular 0.98 ve üstü. `DISTANCE_THRESHOLD` bu iki
aralığı ayıracak şekilde 0.82 olarak belirlendi. Ayrıntılı ölçümler
TESTING.md'de yer almaktadır.

## 07 Haziran 2026

### Hybrid PDF Stratejisi Doğrulaması

Resim ve metin içeren gerçek bir akademik PDF ile hybrid extraction
test edildi. Yalnızca bir figür görselinin içinde geçen bilgi ("Sam
Altman ... CEO") başarıyla retrieve edildi ve doğru yanıtlandı. Bu,
`_ocr_page_images` ile gömülü görsellerin OCR'dan geçirilmesi kararının
gerçek bir senaryoda işe yaradığını doğruladı.
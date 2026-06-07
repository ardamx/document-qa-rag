# TESTING.md

## 06 Haziran 2026

## Test 1: Metin Tabanlı PDF (JIT İmalat Ders Notu)

İlk test olarak JIT (Just-in-Time) imalat ders notu içeren, sadece
metinden oluşan bir `.pdf` dokümanı ile sistemin sınırları test edildi.
Belge slayt formatında, madde işaretli kısa içeriklerden oluşmaktadır
(TPS, kanban, muda/mura/muri, push/pull sistemleri vb.).

Test sürecinde retrieval kalitesi, hallucination kontrolü ve distance
eşiği ampirik olarak kalibre edildi. Bulgular aşağıda kronolojik olarak
verilmiştir.

### Bulgu 1: L2 mesafe metriği güvenilir eşik sağlamadı

ChromaDB varsayılan olarak squared L2 (kare öklid) mesafe kullanmaktadır.
Bu metrikte gözlemlenen değerler güvenilir bir eşik belirlemeye elverişli
değildi:

- Çok alakalı sorular: ~4
- Alakalı sorular: ~9-10
- Alakasız sorular: ~14-15

Alakalı ve alakasız aralıklar birbirine çok yakın olduğu için net bir
kesme noktası belirlenemedi. Örneğin belgede açıkça bulunan "Jidoka"
terimi sorulduğunda mesafe 11-12 çıktı ve doğru chunk ilk sonuçlara
giremedi.

### Bulgu 2: Cosine mesafesine geçiş

Vektör veritabanı kosinüs mesafesi kullanacak şekilde yeniden
yapılandırıldı (`hnsw:space: cosine`). Cosine mesafesinde değerler 0-2
aralığında normalize olmaktadır ve alakalı/alakasız ayrımı belirgin
biçimde netleşti.

### Bulgu 3: Chunk boyutu ve sonuç sayısı kalibrasyonu

Belge slayt formatında kısa maddelerden oluştuğu için başlangıçtaki
büyük chunk boyutu farklı konuları tek parçaya topluyor ve tekil
terimlerin embedding'de kaybolmasına yol açıyordu. Chunk boyutu 200
kelime, örtüşme 40 kelime olarak ayarlandı. Ayrıca getirilen chunk
sayısı (`N_RESULTS`) 3'ten 5'e çıkarıldı.

Bu ayarların etkisi "What is Jidoka?" sorusuyla doğrulandı. Jidoka
terimi belgede yalnızca tek bir yerde, tek satırlık bir madde olarak
geçmektedir. Yapılan değişikliklerden sonra ilgili chunk 4. sırada
(index 3) retrieve edildi:

```
distances: [0.674, 0.686, 0.699, 0.778, 0.780]
```

`N_RESULTS=3` olsaydı bu chunk dışarıda kalacaktı. Sonuç sayısının 5'e
çıkarılması tekil geçişli terimlerin recall'unu artırdı.

LLM doğru ve belgeye sadık yanıtı üretti:

> "Jidoka is a production problem warning system consisting of yellow
> and red lights called andon."

Bu yanıt, belgedeki tanımın birebir karşılığıdır. Chunk içeriği elle
kontrol edildiğinde Jidoka tanımının gerçekten retrieve edilen chunk
içinde yer aldığı doğrulandı; yanıt hallucination değil, bağlamdan
üretilmiştir.

### Bulgu 4: Hallucination guardrail doğrulaması

Guardrail'ın belge dışı sorularda çalıştığı, belgede bulunmayan bir
soruyla test edildi:

| Soru | En yakın distance | Sonuç |
|------|-------------------|-------|
| What is Jidoka? (belgede var, tek geçiş) | 0.674 | Yanıt verildi |
| What is the capital of France? (belgede yok) | 0.980 | Reddedildi |

Belge dışı soru için tüm mesafeler 0.8 eşiğinin üstünde çıktı
(0.980, 0.994, 1.008, 1.032, 1.056) ve sistem soruyu LLM'e
göndermeden "Bu bilgi belgelerde yer almıyor" yanıtını döndürdü.

### Distance eşiği değerlendirmesi

Toplanan verilere göre alakalı ve alakasız soruların mesafe aralıkları
net biçimde ayrışmaktadır:

- Belgede bulunan sorular: 0.67 - 0.78
- Belgede bulunmayan sorular: 0.98+

`DISTANCE_THRESHOLD = 0.8` bu iki aralığın ortasına denk gelmekte ve her
iki yönde de doğru çalışmaktadır. Ancak belgede bulunan en zayıf eşleşme
(0.78) ile eşik (0.80) arasındaki marj dardır; daha zayıf eşleşen geçerli
sorularda yanlış reddetme riski bulunmaktadır.

Dolayısıyla `DISTANCE_THRESHOLD = 0.82` olarak güncellendi.


## Test 2: Görüntü Dosyası — İngilizce (PNG, OCR)

Aynı JIT belgesinin "Terms of TPS" slaytının ekran görüntüsü (PNG)
yüklenerek görüntü → OCR yolu izole test edildi. Bu test, PDF text
layer yerine doğrudan EasyOCR çıktısını değerlendirir.

"What is Yoidon?" sorusu için:

```
distances: [0.662]
```

OCR çıktısı yüksek kalitelidir; slayt neredeyse kusursuz transkript
edilmiştir.

LLM doğru yanıtı üretti:

> "A coordinated approach to simultaneous production of parts for
> assembly."

Distance değeri (0.662), PDF testindeki benzer sorularla (0.67)
neredeyse aynıdır. Bu, OCR yolundan gelen metnin embedding kalitesinin
PDF text layer ile tutarlı olduğunu göstermektedir.

Ayrıca tek bir görüntü kısa bir belge oluşturduğu için yalnızca 1 chunk
üretildi. Sistem `N_RESULTS=5` talebini otomatik olarak mevcut chunk
sayısına (1) düşürdü.

## Test 3: Görüntü Dosyası — Türkçe (PNG, OCR)

Türkçe desteğini doğrulamak için Türkçe bir Wikipedia maddesinin ekran
görüntüsü ("Isı tesiri altındaki bölge") yüklendi.

"ITAB nedir?" sorusu için:

```
distances: [0.660, 0.762]
```

LLM tam ve belgeye sadık yanıtı üretti:

> "Isı tesiri altındaki bölge (ITAB) veya ısıdan etkilenen bölge (IEB),
> erime kaynağında erimemiş ancak kaynak veya ısı yoğun kesme işlemleri
> nedeniyle mikro yapısı ve özellikleri değişmiş olan metal veya
> termoplastik ana malzeme alanıdır."

Türkçe distance değeri (0.660), İngilizce testlerle birebir tutarlıdır.
Bu, kullanılan multilingual embedding modelinin Türkçe ve İngilizce'de
benzer kalitede çalıştığını göstermektedir.

## Test Özeti

| Test | Belge tipi | Dil | Sonuç |
|------|-----------|-----|-------|
| 1 | PDF (text layer + OCR hybrid) | İngilizce | Başarılı |
| 2 | PNG (OCR) | İngilizce | Başarılı |
| 3 | PNG (OCR) | Türkçe | Başarılı |

Üç test de doğru ve bağlama sadık yanıt üretti. Hallucination guardrail
her iki yönde de (alakalı soru kabul, alakasız soru ret) doğrulandı.

## 07 Haziran 2026

## Test 4: Resim + Metin Karışık PDF (Hybrid Strateji Doğrulaması)

Resim ve metin içeren karışık bir PDF'te hybrid extraction stratejisinin
çalıştığını doğrulamak için bir akademik makale (RAG survey, 21 sayfa)
yüklendi. Bu test, en başta tasarlanan "sayfada metin varken gömülü
görsellerin de OCR'dan geçirilmesi" mekanizmasını test etmektedir.

"who is the OpenAI's CEO?" sorusu soruldu. Kritik nokta: "Sam Altman"
bilgisi PDF'in metin katmanında **yer almamaktadır**. Yalnızca Figure 2
içindeki diyagramın görselinde ("Sam Altman Returns to OpenAI as CEO")
geçmektedir.

distances: [0.471, 0.713, 0.731, 0.742, 0.749]

LLM çıktısı:

> "Sam Altman is the CEO of OpenAI."

Bu sonuç, hybrid stratejinin amacını doğrulamaktadır. Distance değeri
(0.471) tüm testler içindeki en düşük değerdir. Bunun nedeni sorunun
("OpenAI's CEO") OCR metniyle ("OpenAI as CEO") neredeyse birebir
örtüşmesidir.

## Güncel Test Özeti

| Test | Belge tipi | Dil | Öne çıkan doğrulama |
|------|-----------|-----|---------------------|
| 1 | PDF (text + OCR hybrid) | İngilizce | Temel akış, distance kalibrasyonu |
| 2 | PNG (OCR) | İngilizce | Görüntü → OCR yolu |
| 3 | PNG (OCR) | Türkçe | Türkçe OCR + multilingual embedding |
| 4 | PDF (resim + metin) | İngilizce | Gömülü görsel OCR retrieval |
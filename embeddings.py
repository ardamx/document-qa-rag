# embeddings.py
from sentence_transformers import SentenceTransformer

# Multilingual model: Türkçe + İngilizce destekli, tamamen local
# İlk çalıştırmada indirilir, sonra cache'den yüklenir
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

_model = None


def get_model() -> SentenceTransformer:
    """Modeli tembel (lazy) yükler, bir kez başlatır."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]:
    """
    Metni kelime bazında örtüşmeli parçalara böler.
    chunk_size: her parçadaki kelime sayısı
    overlap: ardışık parçalar arasında paylaşılan kelime sayısı
             (bağlam kopmasını önler)
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Metin listesini vektörlere çevirir."""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Tek bir sorgu metnini vektöre çevirir."""
    model = get_model()
    embedding = model.encode(query, show_progress_bar=False)
    return embedding.tolist()

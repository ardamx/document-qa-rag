# vectorstore.py
import chromadb

from embeddings import embed_texts, embed_query

# Kalıcı (persistent) ChromaDB istemcisi
# Veriler /app/data altına yazılır (Docker volume ile mount edilir)
_client = chromadb.PersistentClient(path="/app/data")
_collection = _client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)


def reset_collection() -> None:
    """
    Koleksiyonu sıfırlar. Yeni bir belge yüklendiğinde önceki belgenin
    chunk'larının karışmaması için çağrılır.
    """
    global _collection
    _client.delete_collection(name="documents")
    _collection = _client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )


def add_chunks(chunks: list[str]) -> None:
    """Chunk'ları embed edip koleksiyona ekler."""
    if not chunks:
        return
    embeddings = embed_texts(chunks)
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
    )


def query(question: str, n_results: int = 3):
    """
    Soruya en yakın chunk'ları döndürür.
    Dönen değer: (documents, distances)
    distances: küçük = daha yakın/benzer
    """
    q_embedding = embed_query(question)
    results = _collection.query(
        query_embeddings=[q_embedding],
        n_results=n_results,
    )
    documents = results["documents"][0]
    distances = results["distances"][0]
    return documents, distances

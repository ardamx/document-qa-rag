# qa.py
import os

import ollama

from vectorstore import query

# Ollama yapılandırması
# Docker Compose'da servis adı "ollama" olarak geçer; localhost değil
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:12b-it-q4_K_M")

# Retrieval ayarları
N_RESULTS = 3            # kaç chunk getirilecek
DISTANCE_THRESHOLD = 1.0  # bu mesafenin üstü "eşleşme yok" sayılır

# Belge dışı / eşleşmeyen sorular için sabit yanıt
NO_MATCH_MESSAGE = "Bu bilgi belgelerde yer almıyor."

SYSTEM_PROMPT = """Sen bir belge analiz asistanısın. Sana verilen BAĞLAM \
bölümündeki bilgileri kullanarak soruları yanıtla.

Kurallar:
- Yalnızca BAĞLAM'da yer alan bilgileri kullan.
- Bağlamda olmayan bilgileri kesinlikle üretme.
- Eğer sorunun cevabı bağlamda yoksa "Bu bilgi belgelerde yer almıyor" de.
- Yorum yapma, bağlamda ne yazıyorsa ona dayan."""

USER_PROMPT_TEMPLATE = """BAĞLAM:
{context}

SORU:
{question}

YANIT:"""

# Ollama istemcisi (belirtilen host'a bağlanır)
_client = ollama.Client(host=OLLAMA_HOST)


def answer_question(question: str) -> str:
    """
    Soruyu yanıtlar.
    1. İlgili chunk'ları retrieve eder
    2. Similarity threshold ile eşleşme kontrolü yapar (guardrail)
    3. Eşleşme varsa LLM'e bağlamla birlikte gönderir
    """
    documents, distances = query(question, n_results=N_RESULTS)

    # Guardrail 1: hiç sonuç yoksa veya en yakın eşleşme bile uzaksa reddet
    if not documents or min(distances) > DISTANCE_THRESHOLD:
        return NO_MATCH_MESSAGE

    # Eşleşen chunk'ları tek bir bağlam metnine birleştir
    context = "\n\n".join(documents)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )

    response = _client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={
            "num_ctx": 4096,    # context window
            "temperature": 0.1,  # düşük sıcaklık: yaratıcılık değil sadakat
        },
    )

    return response["message"]["content"]

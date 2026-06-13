import voyageai
from src.core.config import settings

_client: voyageai.Client | None = None
VOYAGE_MODEL = "voyage-2"
EXPECTED_DIM = 1024
BATCH_SIZE = 128


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def embed_text(text: str) -> list[float]:
    result = _get_client().embed([text], model=VOYAGE_MODEL)
    embedding = result.embeddings[0]
    if len(embedding) != EXPECTED_DIM:
        raise ValueError(f"Expected {EXPECTED_DIM} dims, got {len(embedding)}")
    return embedding


def embed_step(step_content: str, step_context: str) -> list[float]:
    combined = f"{step_context}\n\n{step_content}" if step_context else step_content
    return embed_text(combined)


def embed_batch(texts: list[str]) -> list[list[float]]:
    results: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = _get_client().embed(batch, model=VOYAGE_MODEL)
        results.extend(response.embeddings)
    return results

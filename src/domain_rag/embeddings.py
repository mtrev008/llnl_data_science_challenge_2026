from __future__ import annotations

import hashlib
import re
import time

import numpy as np

from .config import (
    EMBED_BATCH_SIZE,
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL,
    EMBED_MAX_RETRIES,
    EMBED_RETRY_BASE_SECONDS,
    LOCAL_EMBEDDING_DIMENSIONS,
)

_WORD = re.compile(r"[A-Za-z0-9_]+")


def _local_features(text: str) -> list[str]:
    words = [token.lower() for token in _WORD.findall(text)]
    features = list(words)
    for word in words:
        padded = f"^{word}$"
        features.extend(padded[index:index + 3] for index in range(max(0, len(padded) - 2)))
    return features


def _local_embed_text(text: str, dimensions: int = LOCAL_EMBEDDING_DIMENSIONS) -> list[float]:
    vector = np.zeros(dimensions, dtype=np.float32)
    for feature in _local_features(text):
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        index = value % dimensions
        sign = 1.0 if value & 1 else -1.0
        vector[index] += sign
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector.tolist()


def _openai_embed_texts(texts: list[str], model: str) -> list[list[float]]:
    from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

    client = OpenAI()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        response = None
        for attempt in range(EMBED_MAX_RETRIES + 1):
            try:
                response = client.embeddings.create(
                    model=model,
                    input=batch,
                    encoding_format="float",
                    timeout=60.0,
                )
                break
            except (APIConnectionError, APITimeoutError, RateLimitError):
                if attempt >= EMBED_MAX_RETRIES:
                    raise
                time.sleep(EMBED_RETRY_BASE_SECONDS * (2 ** attempt))
        if response is None:
            raise RuntimeError("Embedding request completed without a response")
        ordered = sorted(response.data, key=lambda item: item.index)
        if len(ordered) != len(batch):
            raise RuntimeError(
                f"Embedding response count mismatch: expected {len(batch)}, got {len(ordered)}"
            )
        dimensions = {len(item.embedding) for item in ordered}
        if len(dimensions) != 1 or not dimensions or next(iter(dimensions)) == 0:
            raise RuntimeError("Embedding response contained invalid vector dimensions")
        vectors.extend(item.embedding for item in ordered)
    return vectors


def embed_texts(texts: list[str], model: str = EMBEDDING_MODEL) -> list[list[float]]:
    if not texts:
        return []
    if EMBEDDING_PROVIDER == "local":
        return [_local_embed_text(text) for text in texts]
    if EMBEDDING_PROVIDER == "openai":
        return _openai_embed_texts(texts, model)
    raise ValueError(
        f"Unsupported RAG_EMBEDDING_PROVIDER={EMBEDDING_PROVIDER!r}; "
        "expected 'local' or 'openai'"
    )


def embed_query(query: str, model: str = EMBEDDING_MODEL) -> list[float]:
    return embed_texts([query], model=model)[0]

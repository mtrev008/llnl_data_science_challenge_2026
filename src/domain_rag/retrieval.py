from __future__ import annotations

import re

import numpy as np

from .config import DEFAULT_TOP_K, EMBEDDING_MODEL, MAX_TOP_K, MIN_RETRIEVAL_SCORE
from .embeddings import embed_query
from .models import SearchResult
from .store import KnowledgeStore

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./+-]+")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "for", "from", "how", "in", "is", "it", "of", "on", "or", "reported",
    "that", "the", "their", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "with",
}


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
        if len(token) > 1 and token.lower() not in _STOPWORDS
    ]


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _heading_overlap(query_tokens: set[str], row: dict) -> float:
    heading_tokens = set(_tokens(f"{row['title']} {row['section']}"))
    if not query_tokens:
        return 0.0
    return len(query_tokens & heading_tokens) / len(query_tokens)


def _snippet(text: str, query_tokens: list[str], limit: int = 500) -> str:
    compact = " ".join(text.split())
    lower = compact.lower()
    positions = [lower.find(token) for token in query_tokens if lower.find(token) >= 0]
    start = max(0, min(positions, default=0) - 100)
    excerpt = compact[start:start + limit]
    if start > 0:
        excerpt = "..." + excerpt
    if start + limit < len(compact):
        excerpt += "..."
    return excerpt


def search_knowledge_base(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    source_contains: str | None = None,
    section_contains: str | None = None,
    source_category: str | None = None,
    min_score: float = MIN_RETRIEVAL_SCORE,
) -> list[SearchResult]:
    if not query.strip():
        raise ValueError("Query cannot be empty")
    top_k = max(1, min(int(top_k), MAX_TOP_K))
    store = KnowledgeStore()
    rows = store.candidate_chunks(source_contains, section_contains, source_category)
    if not rows:
        return []

    query_vector = np.asarray(embed_query(query), dtype=np.float32)
    rows = [
        row for row in rows
        if row["embedding_model"] == EMBEDDING_MODEL and row["embedding"].size == query_vector.size
    ]
    if not rows:
        return []
    query_tokens = _tokens(query)
    lexical = store.lexical_scores(
        query,
        source_contains=source_contains,
        section_contains=section_contains,
        source_category=source_category,
        limit=max(top_k * 20, 100),
    )
    scored: list[dict] = []
    for row in rows:
        lexical_score = lexical.get(row["id"], 0.0)
        semantic_score = _cosine(query_vector, row["embedding"])
        heading_score = _heading_overlap(set(query_tokens), row)
        combined = 0.62 * semantic_score + 0.30 * lexical_score + 0.08 * heading_score
        scored.append(
            {
                "row": row,
                "semantic": semantic_score,
                "lexical": lexical_score,
                "combined": combined,
            }
        )
    scored.sort(key=lambda item: item["combined"], reverse=True)

    selected: list[dict] = []
    candidate_pool = scored[: max(top_k * 8, 30)]
    while candidate_pool and len(selected) < top_k:
        best_index = 0
        best_mmr = float("-inf")
        for index, candidate in enumerate(candidate_pool):
            relevance = candidate["combined"]
            redundancy = max(
                (_cosine(candidate["row"]["embedding"], chosen["row"]["embedding"]) for chosen in selected),
                default=0.0,
            )
            mmr = 0.82 * relevance - 0.18 * redundancy
            if mmr > best_mmr:
                best_mmr = mmr
                best_index = index
        chosen = candidate_pool.pop(best_index)
        if chosen["combined"] >= min_score:
            selected.append(chosen)

    results: list[SearchResult] = []
    for item in selected:
        row = item["row"]
        results.append(
            SearchResult(
                id=row["id"],
                score=round(float(item["combined"]), 6),
                semantic_score=round(float(item["semantic"]), 6),
                lexical_score=round(float(item["lexical"]), 6),
                title=row["title"],
                source_path=row["source_path"],
                section=row["section"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                snippet=_snippet(row["text"], query_tokens),
                metadata=row["metadata"],
            )
        )
    return results

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LoadedUnit:
    text: str
    title: str
    source_path: str
    page: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    id: str
    document_id: str
    source_path: str
    title: str
    section: str
    page_start: int | None
    page_end: int | None
    chunk_index: int
    text: str
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    source_category: str = "document"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    id: str
    score: float
    semantic_score: float
    lexical_score: float
    title: str
    source_path: str
    section: str
    page_start: int | None
    page_end: int | None
    snippet: str
    metadata: dict[str, Any] = field(default_factory=dict)

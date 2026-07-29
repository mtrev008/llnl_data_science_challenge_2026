from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
RAG_HOME = Path(os.getenv("RAG_HOME", PROJECT_ROOT / ".rag_data")).expanduser().resolve()
DB_PATH = Path(os.getenv("RAG_DB_PATH", RAG_HOME / "knowledge.db")).expanduser().resolve()

EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "local").strip().lower()
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "local-feature-hash-v1" if EMBEDDING_PROVIDER == "local" else "text-embedding-3-small",
)
LOCAL_EMBEDDING_DIMENSIONS = int(os.getenv("RAG_LOCAL_EMBEDDING_DIMENSIONS", "2048"))
ANSWER_MODEL = os.getenv("RAG_ANSWER_MODEL", "gpt-5.6")

MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "4200"))
CHUNK_OVERLAP_CHARS = int(os.getenv("RAG_CHUNK_OVERLAP_CHARS", "600"))
EMBED_BATCH_SIZE = int(os.getenv("RAG_EMBED_BATCH_SIZE", "64"))
EMBED_MAX_RETRIES = int(os.getenv("RAG_EMBED_MAX_RETRIES", "3"))
EMBED_RETRY_BASE_SECONDS = float(os.getenv("RAG_EMBED_RETRY_BASE_SECONDS", "1.0"))
DEFAULT_TOP_K = int(os.getenv("RAG_DEFAULT_TOP_K", "6"))
MAX_TOP_K = int(os.getenv("RAG_MAX_TOP_K", "12"))
MIN_RETRIEVAL_SCORE = float(os.getenv("RAG_MIN_RETRIEVAL_SCORE", "0.12"))

LOADER_VERSION = "2"
CHUNKER_VERSION = "2"

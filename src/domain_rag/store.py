from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from .config import DB_PATH
from .models import Chunk


class KnowledgeStore:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    content_sha256 TEXT,
                    file_size INTEGER,
                    file_mtime_ns INTEGER,
                    loader_version TEXT,
                    chunker_version TEXT,
                    embedding_model TEXT,
                    embedding_dimensions INTEGER,
                    source_category TEXT NOT NULL DEFAULT 'document',
                    extraction_status TEXT NOT NULL DEFAULT 'ok',
                    warnings_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    section TEXT NOT NULL,
                    page_start INTEGER,
                    page_end INTEGER,
                    chunk_index INTEGER NOT NULL,
                    previous_chunk_id TEXT,
                    next_chunk_id TEXT,
                    source_category TEXT NOT NULL DEFAULT 'document',
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    embedding_dimensions INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_path);
                CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks(section);
                """
            )
            self._add_missing_columns(
                connection,
                "documents",
                {
                    "content_sha256": "TEXT",
                    "file_size": "INTEGER",
                    "file_mtime_ns": "INTEGER",
                    "loader_version": "TEXT",
                    "chunker_version": "TEXT",
                    "embedding_model": "TEXT",
                    "embedding_dimensions": "INTEGER",
                    "source_category": "TEXT NOT NULL DEFAULT 'document'",
                    "extraction_status": "TEXT NOT NULL DEFAULT 'ok'",
                    "warnings_json": "TEXT NOT NULL DEFAULT '[]'",
                },
            )
            self._add_missing_columns(
                connection,
                "chunks",
                {
                    "previous_chunk_id": "TEXT",
                    "next_chunk_id": "TEXT",
                    "source_category": "TEXT NOT NULL DEFAULT 'document'",
                },
            )
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    id UNINDEXED,
                    title,
                    section,
                    text,
                    source_path UNINDEXED,
                    source_category UNINDEXED
                )
                """
            )
            indexed = connection.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            chunks = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            if indexed != chunks:
                connection.execute("DELETE FROM chunks_fts")
                connection.execute(
                    """
                    INSERT INTO chunks_fts(id, title, section, text, source_path, source_category)
                    SELECT id, title, section, text, source_path, source_category FROM chunks
                    """
                )

    @staticmethod
    def _add_missing_columns(
        connection: sqlite3.Connection,
        table: str,
        columns: dict[str, str],
    ) -> None:
        existing = {
            row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, declaration in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

    def replace_document(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        embedding_model: str,
        *,
        content_sha256: str | None = None,
        file_size: int | None = None,
        file_mtime_ns: int | None = None,
        loader_version: str | None = None,
        chunker_version: str | None = None,
        extraction_status: str = "ok",
        warnings: list[str] | None = None,
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have one embedding")
        dimensions = {len(vector) for vector in embeddings}
        if len(dimensions) != 1 or not dimensions or next(iter(dimensions)) == 0:
            raise ValueError("Embeddings must have one consistent nonzero dimension")

        first = chunks[0]
        with self.connect() as connection:
            old = connection.execute(
                "SELECT document_id FROM documents WHERE source_path = ?", (first.source_path,)
            ).fetchone()
            if old:
                old_ids = connection.execute(
                    "SELECT id FROM chunks WHERE document_id = ?", (old["document_id"],)
                ).fetchall()
                connection.executemany(
                    "DELETE FROM chunks_fts WHERE id = ?",
                    [(row["id"],) for row in old_ids],
                )
                connection.execute("DELETE FROM chunks WHERE document_id = ?", (old["document_id"],))
                connection.execute("DELETE FROM documents WHERE document_id = ?", (old["document_id"],))

            connection.execute(
                """
                INSERT INTO documents(
                    document_id, source_path, title, chunk_count, content_sha256,
                    file_size, file_mtime_ns, loader_version, chunker_version,
                    embedding_model, embedding_dimensions, source_category,
                    extraction_status, warnings_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    first.document_id,
                    first.source_path,
                    first.title,
                    len(chunks),
                    content_sha256,
                    file_size,
                    file_mtime_ns,
                    loader_version,
                    chunker_version,
                    embedding_model,
                    next(iter(dimensions)),
                    first.source_category,
                    extraction_status,
                    json.dumps(warnings or [], ensure_ascii=False),
                ),
            )
            rows = []
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                vector = np.asarray(embedding, dtype=np.float32)
                rows.append(
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.source_path,
                        chunk.title,
                        chunk.section,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.chunk_index,
                        chunk.previous_chunk_id,
                        chunk.next_chunk_id,
                        chunk.source_category,
                        chunk.text,
                        vector.tobytes(),
                        int(vector.size),
                        embedding_model,
                        json.dumps(chunk.metadata, ensure_ascii=False, default=str),
                    )
                )
            connection.executemany(
                """
                INSERT INTO chunks(
                    id, document_id, source_path, title, section, page_start, page_end,
                    chunk_index, previous_chunk_id, next_chunk_id, source_category,
                    text, embedding, embedding_dimensions, embedding_model, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.executemany(
                """
                INSERT INTO chunks_fts(id, title, section, text, source_path, source_category)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.title,
                        chunk.section,
                        chunk.text,
                        chunk.source_path,
                        chunk.source_category,
                    )
                    for chunk in chunks
                ],
            )

    def document_status(self, source_path: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE source_path = ?", (source_path,)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["warnings"] = json.loads(item.pop("warnings_json"))
        return item

    def candidate_chunks(
        self,
        source_contains: str | None = None,
        section_contains: str | None = None,
        source_category: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        values: list[str] = []
        if source_contains:
            clauses.append("LOWER(source_path) LIKE ?")
            values.append(f"%{source_contains.lower()}%")
        if section_contains:
            clauses.append("LOWER(section) LIKE ?")
            values.append(f"%{section_contains.lower()}%")
        if source_category:
            clauses.append("LOWER(source_category) = ?")
            values.append(source_category.lower())
        if not section_contains:
            clauses.append("LOWER(section) NOT LIKE '%references%'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM chunks {where} ORDER BY source_path, chunk_index"
        with self.connect() as connection:
            rows = connection.execute(query, values).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["embedding"] = np.frombuffer(
                item["embedding"], dtype=np.float32, count=item["embedding_dimensions"]
            ).copy()
            item["metadata"] = json.loads(item.pop("metadata_json"))
            output.append(item)
        return output

    def lexical_scores(
        self,
        query: str,
        source_contains: str | None = None,
        section_contains: str | None = None,
        source_category: str | None = None,
        limit: int = 100,
    ) -> dict[str, float]:
        stopwords = {
            "a", "an", "and", "are", "as", "at", "be", "by", "did", "do",
            "does", "for", "from", "how", "in", "is", "it", "of", "on", "or",
            "reported", "that", "the", "their", "this", "to", "was", "were",
            "what", "when", "where", "which", "who", "why", "with",
        }
        tokens = [
            token
            for token in re.findall(r"[A-Za-z0-9_]+", query)
            if len(token) > 1 and token.lower() not in stopwords
        ]
        if not tokens:
            return {}
        terms: list[str] = []
        for token in tokens:
            lowered = token.lower()
            terms.append(f'"{lowered}"')
            stem = lowered
            for suffix in ("izations", "ization", "ations", "ation", "ments", "ment", "ing", "ed", "es", "s"):
                if stem.endswith(suffix) and len(stem) - len(suffix) >= 4:
                    stem = stem[: -len(suffix)]
                    break
            if stem != lowered:
                terms.append(f"{stem}*")
        match = " OR ".join(dict.fromkeys(terms))
        clauses = ["chunks_fts MATCH ?"]
        values: list[object] = [match]
        if source_contains:
            clauses.append("LOWER(source_path) LIKE ?")
            values.append(f"%{source_contains.lower()}%")
        if section_contains:
            clauses.append("LOWER(section) LIKE ?")
            values.append(f"%{section_contains.lower()}%")
        if source_category:
            clauses.append("LOWER(source_category) = ?")
            values.append(source_category.lower())
        if not section_contains:
            clauses.append("LOWER(section) NOT LIKE '%references%'")
        values.append(max(1, int(limit)))
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, bm25(chunks_fts, 0.0, 1.5, 3.0, 1.0, 0.0, 0.0) AS rank
                FROM chunks_fts
                WHERE {' AND '.join(clauses)}
                ORDER BY rank
                LIMIT ?
                """,
                values,
            ).fetchall()
        if not rows:
            return {}
        strengths = {row["id"]: 1.0 / (1.0 + max(0.0, float(row["rank"]))) for row in rows}
        maximum = max(strengths.values())
        return {key: value / maximum for key, value in strengths.items()}

    def get_chunk(self, chunk_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item.pop("embedding")
        item.pop("embedding_dimensions")
        item["metadata"] = json.loads(item.pop("metadata_json"))
        return item

    def get_adjacent_chunks(self, chunk_id: str, distance: int = 1) -> list[dict]:
        distance = max(0, min(int(distance), 2))
        with self.connect() as connection:
            anchor = connection.execute(
                "SELECT document_id, chunk_index FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
            if not anchor:
                return []
            rows = connection.execute(
                """
                SELECT * FROM chunks
                WHERE document_id = ? AND chunk_index BETWEEN ? AND ?
                ORDER BY chunk_index
                """,
                (
                    anchor["document_id"],
                    anchor["chunk_index"] - distance,
                    anchor["chunk_index"] + distance,
                ),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item.pop("embedding")
            item.pop("embedding_dimensions")
            item["metadata"] = json.loads(item.pop("metadata_json"))
            output.append(item)
        return output

    def list_documents(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, source_path, title, chunk_count, content_sha256,
                       file_size, loader_version, chunker_version, embedding_model,
                       embedding_dimensions, source_category, extraction_status,
                       warnings_json, updated_at
                FROM documents ORDER BY title
                """
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["warnings"] = json.loads(item.pop("warnings_json"))
            output.append(item)
        return output

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .chunking import build_chunks
from .config import CHUNKER_VERSION, EMBEDDING_MODEL, LOADER_VERSION
from .embeddings import embed_texts
from .loaders import discover_files, load_file
from .store import KnowledgeStore


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _embedding_text(chunk) -> str:
    page = (
        f"{chunk.page_start}-{chunk.page_end}"
        if chunk.page_start is not None and chunk.page_end != chunk.page_start
        else str(chunk.page_start or "n/a")
    )
    return (
        f"Document: {chunk.title}\n"
        f"Section: {chunk.section}\n"
        f"Pages or rows: {page}\n\n"
        f"{chunk.text}"
    )


def ingest_path(path: str | Path) -> dict:
    files = discover_files(path)
    store = KnowledgeStore()
    summaries: list[dict] = []
    for file_path in files:
        source = str(file_path.resolve())
        try:
            stat = file_path.stat()
            content_sha256 = _sha256(file_path)
            current = store.document_status(source)
            if (
                current
                and current["content_sha256"] == content_sha256
                and current["loader_version"] == LOADER_VERSION
                and current["chunker_version"] == CHUNKER_VERSION
                and current["embedding_model"] == EMBEDDING_MODEL
            ):
                summaries.append(
                    {
                        "source": source,
                        "status": "unchanged",
                        "document_hash": content_sha256,
                        "chunk_count": current["chunk_count"],
                        "warnings": current["warnings"],
                    }
                )
                continue

            units = load_file(file_path)
            diagnostics = (
                units[0].metadata.get("extraction_diagnostics", {}) if units else {}
            )
            extraction_status = diagnostics.get(
                "extraction_status",
                "OCR_REQUIRED" if file_path.suffix.lower() == ".pdf" and not units else "ok",
            )
            warnings = list(diagnostics.get("extraction_warnings", []))
            if not units and extraction_status == "OCR_REQUIRED":
                warnings.append("No extractable PDF text was available for indexing.")
            chunks = build_chunks(units)
            if not chunks:
                summaries.append(
                    {
                        "source": source,
                        "status": "skipped",
                        "document_hash": content_sha256,
                        "extraction_status": extraction_status,
                        "reason": "no extractable text",
                        "warnings": list(dict.fromkeys(warnings)),
                    }
                )
                continue
            embeddings = embed_texts([_embedding_text(chunk) for chunk in chunks])
            store.replace_document(
                chunks,
                embeddings,
                EMBEDDING_MODEL,
                content_sha256=content_sha256,
                file_size=stat.st_size,
                file_mtime_ns=stat.st_mtime_ns,
                loader_version=LOADER_VERSION,
                chunker_version=CHUNKER_VERSION,
                extraction_status=extraction_status,
                warnings=warnings,
            )
            summaries.append(
                {
                    "source": source,
                    "status": "indexed",
                    "document_hash": content_sha256,
                    "chunk_count": len(chunks),
                    "extraction_status": extraction_status,
                    "warnings": warnings,
                }
            )
        except Exception as error:
            summaries.append(
                {
                    "source": source,
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "warnings": [],
                }
            )
    counts = {
        status: sum(1 for item in summaries if item["status"] == status)
        for status in ("indexed", "unchanged", "skipped", "failed")
    }
    return {"files_processed": len(files), "status_counts": counts, "results": summaries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents and datasets into the local RAG database.")
    parser.add_argument("path", help="A supported file or directory")
    args = parser.parse_args()
    result = ingest_path(args.path)
    for item in result["results"]:
        print(item)


if __name__ == "__main__":
    main()

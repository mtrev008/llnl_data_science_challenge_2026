"""Offline contract tests for domain RAG ingestion and MCP integration."""

from __future__ import annotations

import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib-domain-rag"))
sys.path.insert(0, str(ROOT / "src"))

from domain_rag.chunking import build_chunks  # noqa: E402
from domain_rag.config import PROJECT_ROOT  # noqa: E402
from domain_rag.ingest import ingest_path  # noqa: E402
from domain_rag.models import Chunk, LoadedUnit  # noqa: E402
from domain_rag.retrieval import search_knowledge_base  # noqa: E402
from domain_rag.config import EMBEDDING_MODEL  # noqa: E402
from domain_rag.config import EMBEDDING_PROVIDER  # noqa: E402
from domain_rag.embeddings import embed_texts  # noqa: E402
from domain_rag.store import KnowledgeStore  # noqa: E402
import mcp_server as server  # noqa: E402


class DomainRagTests(unittest.TestCase):
    def test_default_embeddings_are_local_and_semantically_shape_related(self) -> None:
        self.assertEqual(EMBEDDING_PROVIDER, "local")
        self.assertEqual(EMBEDDING_MODEL, "local-feature-hash-v1")
        vectors = np.asarray(
            embed_texts(
                [
                    "align the lattice model with computed tomography",
                    "lattice alignment and registration in the CT volume",
                    "pharmaceutical tablet color",
                ]
            ),
            dtype=np.float32,
        )
        related = float(np.dot(vectors[0], vectors[1]))
        unrelated = float(np.dot(vectors[0], vectors[2]))
        self.assertGreater(related, unrelated)

    def test_project_root_is_repository(self) -> None:
        self.assertEqual(PROJECT_ROOT, ROOT.resolve())

    def test_section_chunking_preserves_source_and_page(self) -> None:
        units = [
            LoadedUnit(
                text=(
                    "Abstract\nA compact summary of the study.\n\n"
                    "2 Methods\nThe lattice was evaluated with a bounded method."
                ),
                title="Example paper",
                source_path=str(ROOT / "papers" / "example.pdf"),
                page=3,
                metadata={"kind": "paper", "file_type": "pdf"},
            )
        ]

        chunks = build_chunks(units)

        self.assertEqual([chunk.section for chunk in chunks], ["Abstract", "2 Methods"])
        self.assertTrue(all(chunk.page_start == 3 for chunk in chunks))
        self.assertTrue(all(chunk.source_path == units[0].source_path for chunk in chunks))
        self.assertTrue(all(chunk.id for chunk in chunks))
        self.assertIsNone(chunks[0].previous_chunk_id)
        self.assertEqual(chunks[0].next_chunk_id, chunks[1].id)
        self.assertEqual(chunks[1].previous_chunk_id, chunks[0].id)

    def test_numbered_subsections_preserve_hierarchy(self) -> None:
        chunks = build_chunks(
            [
                LoadedUnit(
                    text=(
                        "2 Methods\nGeneral method description.\n\n"
                        "2.1 Segmentation\nThresholding details."
                    ),
                    title="Hierarchy",
                    source_path=str(ROOT / "hierarchy.md"),
                    metadata={"kind": "paper"},
                )
            ]
        )

        self.assertEqual(chunks[0].section, "2 Methods")
        self.assertEqual(chunks[1].section, "2 Methods > 2.1 Segmentation")

    def test_ieee_split_headings_and_references_are_bounded(self) -> None:
        chunks = build_chunks(
            [
                LoadedUnit(
                    text=(
                        "I. I\n"
                        "NTRODUCTION\n"
                        "The paper introduces the method.\n\n"
                        "X. D\n"
                        "ISCUSSION AND LIMITA TIONS\n"
                        "The method has bounded limitations.\n\n"
                        "REFERENCES\n"
                        "[1] A. Author, Journal title, vol. 2, pp. 1-4.\n"
                        "Science Division, Lawrence Livermore National Laboratory\n"
                        "3 024002\n"
                    ),
                    title="IEEE paper",
                    source_path=str(ROOT / "ieee.pdf"),
                    page=1,
                    metadata={"kind": "paper"},
                )
            ]
        )

        sections = [chunk.section for chunk in chunks]
        self.assertEqual(
            sections,
            ["I. Introduction", "X. Discussion and Limitations", "References"],
        )
        self.assertIn("Science Division", chunks[-1].text)
        self.assertFalse(any("Author" in section for section in sections))

    def test_sqlite_store_round_trip_preserves_citation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = KnowledgeStore(Path(temporary) / "knowledge.db")
            chunk = Chunk(
                id="chunk-1",
                document_id="document-1",
                source_path=str(ROOT / "papers" / "example.pdf"),
                title="Example paper",
                section="Methods",
                page_start=4,
                page_end=5,
                chunk_index=0,
                text="Evidence text.",
                metadata={"kind": "paper"},
            )
            store.replace_document(
                [chunk],
                [np.asarray([1.0, 0.0, 0.5], dtype=np.float32).tolist()],
                "test-embedding",
            )

            fetched = store.get_chunk("chunk-1")
            sources = store.list_documents()

        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["section"], "Methods")
        self.assertEqual(fetched["page_start"], 4)
        self.assertEqual(fetched["page_end"], 5)
        self.assertEqual(fetched["metadata"]["kind"], "paper")
        self.assertEqual(sources[0]["chunk_count"], 1)

    def test_failed_replacement_preserves_previous_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = KnowledgeStore(Path(temporary) / "knowledge.db")
            chunk = Chunk(
                id="stable",
                document_id="document",
                source_path=str(ROOT / "stable.md"),
                title="Stable",
                section="Results",
                page_start=1,
                page_end=1,
                chunk_index=0,
                text="Stable evidence.",
            )
            store.replace_document([chunk], [[1.0, 0.0]], "test")
            with self.assertRaises(ValueError):
                store.replace_document([chunk], [[]], "test")

            fetched = store.get_chunk("stable")

        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["text"], "Stable evidence.")

    def test_fts_bm25_and_adjacent_chunk_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = KnowledgeStore(Path(temporary) / "knowledge.db")
            chunks = [
                Chunk(
                    id=f"chunk-{index}",
                    document_id="document",
                    source_path=str(ROOT / "paper.md"),
                    title="Paper",
                    section=section,
                    page_start=index + 1,
                    page_end=index + 1,
                    chunk_index=index,
                    text=text,
                    previous_chunk_id=f"chunk-{index - 1}" if index else None,
                    next_chunk_id=f"chunk-{index + 1}" if index < 2 else None,
                    source_category="paper",
                )
                for index, (section, text) in enumerate(
                    [
                        ("Introduction", "Background lattice material."),
                        ("Methods > Segmentation", "Adaptive threshold segmentation method."),
                        ("Results", "Evaluation and accuracy results."),
                    ]
                )
            ]
            store.replace_document(
                chunks,
                [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]],
                "test",
            )

            lexical = store.lexical_scores("adaptive threshold segmentation")
            neighbors = store.get_adjacent_chunks("chunk-1", distance=1)

        self.assertEqual(max(lexical, key=lexical.get), "chunk-1")
        self.assertEqual([item["id"] for item in neighbors], ["chunk-0", "chunk-1", "chunk-2"])

    def test_unchanged_ingestion_skips_second_embedding_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "paper.md"
            source.write_text("# Methods\nBounded segmentation method.", encoding="utf-8")
            store = KnowledgeStore(root / "knowledge.db")
            with (
                patch("domain_rag.ingest.KnowledgeStore", return_value=store),
                patch(
                    "domain_rag.ingest.embed_texts",
                    return_value=[[1.0, 0.0]],
                ) as embed,
            ):
                first = ingest_path(source)
                second = ingest_path(source)

        self.assertEqual(first["results"][0]["status"], "indexed")
        self.assertEqual(second["results"][0]["status"], "unchanged")
        self.assertEqual(embed.call_count, 1)

    def test_retrieval_evaluation_answerable_and_unanswerable(self) -> None:
        evaluation = json.loads(
            (
                ROOT / "tests" / "fixtures" / "domain_rag" / "evaluation.json"
            ).read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            store = KnowledgeStore(Path(temporary) / "knowledge.db")
            chunks = [
                Chunk(
                    id="methods",
                    document_id="evaluation",
                    source_path=str(ROOT / "evaluation-paper.md"),
                    title="Evaluation paper",
                    section="Methods > Segmentation",
                    page_start=2,
                    page_end=2,
                    chunk_index=0,
                    text="The study used an adaptive threshold segmentation method.",
                    source_category="paper",
                ),
                Chunk(
                    id="results",
                    document_id="evaluation",
                    source_path=str(ROOT / "evaluation-paper.md"),
                    title="Evaluation paper",
                    section="Results",
                    page_start=3,
                    page_end=3,
                    chunk_index=1,
                    text="Segmentation accuracy was evaluated on the lattice.",
                    source_category="paper",
                ),
            ]
            store.replace_document(
                chunks,
                [[1.0, 0.0], [0.0, 1.0]],
                EMBEDDING_MODEL,
            )
            with patch("domain_rag.retrieval.KnowledgeStore", return_value=store):
                with patch("domain_rag.retrieval.embed_query", return_value=[1.0, 0.0]):
                    answerable = search_knowledge_base(evaluation[0]["question"], top_k=2)
                with patch("domain_rag.retrieval.embed_query", return_value=[0.0, 0.0]):
                    unanswerable = search_knowledge_base(
                        evaluation[1]["question"],
                        top_k=2,
                    )

        self.assertTrue(answerable)
        self.assertEqual(answerable[0].section, evaluation[0]["expected_section"])
        self.assertIn(evaluation[0]["expected_source"], answerable[0].source_path)
        self.assertEqual(unanswerable, [])

    def test_consolidated_server_exposes_domain_tools(self) -> None:
        for tool_name in (
            "search_domain_knowledge",
            "fetch_domain_chunk",
            "list_domain_sources",
            "ingest_domain_sources",
        ):
            self.assertTrue(callable(getattr(server, tool_name)))

    def test_ingestion_path_rejects_generated_database_directory(self) -> None:
        rag_data = ROOT / ".rag_data"
        rag_data.mkdir(exist_ok=True)
        with self.assertRaises(PermissionError):
            server._validate_domain_ingestion_path(str(rag_data))


if __name__ == "__main__":
    unittest.main()

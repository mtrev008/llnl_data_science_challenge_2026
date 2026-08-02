"""Run a readable, offline evaluation of the three-paper XCT RAG corpus."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sys

import numpy as np


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

OUTPUT = ROOT / "outputs" / "domain_rag_evaluation" / "xct_core"
DATABASE = OUTPUT / "knowledge.db"
os.environ["RAG_DB_PATH"] = str(DATABASE)

from domain_rag.chunking import build_chunks  # noqa: E402
from domain_rag.ingest import ingest_path  # noqa: E402
from domain_rag.loaders import load_file  # noqa: E402
from domain_rag.config import EMBEDDING_MODEL, EMBEDDING_PROVIDER  # noqa: E402
from domain_rag.retrieval import search_knowledge_base  # noqa: E402
from domain_rag.store import KnowledgeStore  # noqa: E402


PAPERS = [
    ROOT / "references" / "papers"
    / "LatticeAnalytics-Strut-Level-Visualization-and-Inspection-of-Additively-Manufactured-Lattice.pdf",
    ROOT / "references" / "papers" / "TheRoleofX-rayCTinAMupdated.pdf",
    ROOT / "references" / "papers"
    / "X-ray computed tomography for additive manufacture a review_unformatted.pdf",
]

QUESTIONS = [
    (
        "What problem is LatticeAnalytics designed to solve?",
        "LatticeAnalytics",
        ("abstract", "introduction", "document overview"),
    ),
    (
        "How are the nominal lattice model and XCT volume aligned?",
        "LatticeAnalytics",
        ("alignment", "registration", "method", "system"),
    ),
    (
        "Why does the framework extract individual strut subvolumes?",
        "LatticeAnalytics",
        ("strut", "method", "system", "design"),
    ),
    (
        "Which visualizations support strut defect inspection?",
        "LatticeAnalytics",
        ("visual", "method", "design"),
    ),
    (
        "What limitations do the LatticeAnalytics authors report?",
        "LatticeAnalytics",
        ("discussion", "limitation"),
    ),
    (
        "Why are external inspection techniques insufficient for many AM parts?",
        "TheRoleofX-rayCTinAMupdated",
        ("introduction", "document overview"),
    ),
    (
        "What roles can computed tomography perform in additive manufacturing inspection?",
        "TheRoleofX-rayCTinAMupdated",
        ("computed tomography", "inspection", "document overview"),
    ),
    (
        "How does CT relate to nondestructive testing and dimensional metrology?",
        "TheRoleofX-rayCTinAMupdated",
        ("metrology", "testing", "document overview"),
    ),
    (
        "What internal flaws motivate CT inspection?",
        "TheRoleofX-rayCTinAMupdated",
        ("introduction", "flaw", "defect", "document overview"),
    ),
    (
        "What CT measurement challenges are described?",
        "TheRoleofX-rayCTinAMupdated",
        ("challenge", "limitation", "conclusion", "document overview"),
    ),
    (
        "Why is volumetric dimensional measurement important for additive manufactured parts?",
        "X-ray computed tomography for additive manufacture",
        ("introduction", "dimensional"),
    ),
    (
        "How did XCT transition from imaging to industrial metrology?",
        "X-ray computed tomography for additive manufacture",
        ("metrology", "introduction"),
    ),
    (
        "How is XCT used for porosity measurement?",
        "X-ray computed tomography for additive manufacture",
        ("porosity",),
    ),
    (
        "How is XCT used for dimensional measurement?",
        "X-ray computed tomography for additive manufacture",
        ("dimensional",),
    ),
    (
        "What barriers to continued XCT adoption are identified?",
        "X-ray computed tomography for additive manufacture",
        ("conclusion", "limitation", "barrier"),
    ),
]

UNSUPPORTED = [
    "What is the calibrated voxel size of the LLNL challenge CT volume?",
    "What defect diameter threshold determines acceptance for the LLNL specimen?",
    "What registration transform maps the challenge JSON to its TIFF?",
    "Which observed struts are intentional design deviations?",
    "What TIFF intensity represents physical density?",
]

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        resolved = OUTPUT.resolve()
        expected_parent = (ROOT / "outputs" / "domain_rag_evaluation").resolve()
        if expected_parent not in resolved.parents:
            raise RuntimeError(f"Refusing to replace unexpected output path: {resolved}")
        shutil.rmtree(resolved)
    OUTPUT.mkdir(parents=True)

    extraction_lines = [
        "# XCT core extraction and chunking report",
        "",
        "This report was generated without network or embedding API calls.",
        "",
    ]
    extraction_pass = True
    for paper in PAPERS:
        units = load_file(paper)
        chunks = build_chunks(units)
        diagnostics = units[0].metadata.get("extraction_diagnostics", {}) if units else {}
        section_names = list(dict.fromkeys(chunk.section for chunk in chunks))
        lengths = [len(chunk.text) for chunk in chunks]
        pages = diagnostics.get("total_pages", 0)
        text_pages = diagnostics.get("pages_with_text", 0)
        coverage = text_pages / pages if pages else 0.0
        passed = bool(chunks) and diagnostics.get("extraction_status") != "OCR_REQUIRED"
        extraction_pass &= passed
        extraction_lines.extend(
            [
                f"## {paper.name}",
                "",
                f"- SHA-256: `{sha256(paper)}`",
                f"- File size: {paper.stat().st_size:,} bytes",
                f"- Pages: {pages}",
                f"- Pages with text: {text_pages}",
                f"- Text-page coverage: {coverage:.1%}",
                f"- Extraction status: `{diagnostics.get('extraction_status', 'unknown')}`",
                f"- Chunk count: {len(chunks)}",
                (
                    f"- Chunk characters: min {min(lengths)}, "
                    f"median {int(np.median(lengths))}, max {max(lengths)}"
                    if lengths else "- Chunk characters: unavailable"
                ),
                f"- Chunks missing pages: {sum(chunk.page_start is None for chunk in chunks)}",
                f"- Result: `{'PASS' if passed else 'FAIL'}`",
                "",
                "Detected sections:",
                "",
                *[f"- {section}" for section in section_names],
                "",
            ]
        )

    (OUTPUT / "extraction_report.md").write_text(
        "\n".join(extraction_lines),
        encoding="utf-8",
    )
    if not extraction_pass:
        (OUTPUT / "execution_log.txt").write_text(
            "OFFLINE_EXTRACTION_FAILED\n",
            encoding="utf-8",
        )
        return 1

    store = KnowledgeStore(DATABASE)
    first_results = [ingest_path(paper)["results"][0] for paper in PAPERS]
    second_results = [ingest_path(paper)["results"][0] for paper in PAPERS]

    retrieval_rows = []
    reciprocal_ranks = []
    recall_at_five = []
    citation_failures = []
    for question, expected_source, expected_sections in QUESTIONS:
        results = search_knowledge_base(question, top_k=5, min_score=0.12)
        source_ranks = [
            rank
            for rank, result in enumerate(results, start=1)
            if expected_source.lower() in Path(result.source_path).name.lower()
        ]
        rank = source_ranks[0] if source_ranks else None
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        recall_at_five.append(bool(rank))
        section_hit = any(
            any(term in result.section.lower() for term in expected_sections)
            and expected_source.lower() in Path(result.source_path).name.lower()
            for result in results
        )
        fetched = [store.get_chunk(result.id) for result in results[:3]]
        for result, chunk in zip(results[:3], fetched, strict=True):
            if (
                chunk is None
                or chunk["source_path"] != result.source_path
                or chunk["section"] != result.section
                or chunk["page_start"] != result.page_start
            ):
                citation_failures.append(result.id)
        retrieval_rows.append(
            (question, expected_source, rank, section_hit, results)
        )

    unsupported_results = [
        (question, search_knowledge_base(question, top_k=5, min_score=0.12))
        for question in UNSUPPORTED
    ]
    source_filtered = search_knowledge_base(
        "computed tomography dimensional metrology",
        top_k=5,
        source_contains="TheRoleofX-rayCTinAMupdated",
        min_score=0.0,
    )
    section_filtered = search_knowledge_base(
        "porosity measurement",
        top_k=5,
        section_contains="pore measurements",
        min_score=0.0,
    )
    category_filtered = search_knowledge_base(
        "lattice inspection",
        top_k=5,
        source_category="paper",
        min_score=0.0,
    )

    filter_pass = (
        bool(source_filtered)
        and all(
            "TheRoleofX-rayCTinAMupdated" in Path(item.source_path).name
            for item in source_filtered
        )
        and bool(section_filtered)
        and all("pore measurements" in item.section.lower() for item in section_filtered)
        and bool(category_filtered)
        and all(item.metadata.get("kind") == "paper" for item in category_filtered)
    )

    adjacency_pass = True
    adjacency_notes = []
    for document in store.list_documents():
        rows = store.candidate_chunks(source_contains=Path(document["source_path"]).name)
        if len(rows) < 2:
            continue
        anchor = rows[len(rows) // 2]
        neighbors = store.get_adjacent_chunks(anchor["id"], distance=1)
        same_document = all(
            neighbor["document_id"] == anchor["document_id"] for neighbor in neighbors
        )
        bounded = len(neighbors) <= 3
        adjacency_pass &= same_document and bounded
        adjacency_notes.append(
            f"- `{Path(document['source_path']).name}`: "
            f"{len(neighbors)} chunks, same document={same_document}, bounded={bounded}"
        )

    recall = sum(recall_at_five) / len(recall_at_five)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    section_accuracy = sum(row[3] for row in retrieval_rows) / len(retrieval_rows)
    unchanged_pass = all(item["status"] == "unchanged" for item in second_results)
    citation_pass = not citation_failures
    overall = (
        recall >= 0.80
        and mrr >= 0.65
        and section_accuracy >= 0.75
        and unchanged_pass
        and citation_pass
        and adjacency_pass
        and filter_pass
    )

    lines = [
        "# XCT core offline RAG evaluation",
        "",
        f"> Retrieval provider: `{EMBEDDING_PROVIDER}`",
        f"> Embedding model: `{EMBEDDING_MODEL}`",
        "> This run uses the real local pipeline and makes no network calls.",
        "",
        "## Summary",
        "",
        f"- Overall offline result: `{'PASS' if overall else 'FAIL'}`",
        f"- Expected-paper Recall@5: {recall:.3f}",
        f"- Mean reciprocal rank: {mrr:.3f}",
        f"- Expected-section accuracy: {section_accuracy:.3f}",
        f"- Unchanged re-ingestion: `{'PASS' if unchanged_pass else 'FAIL'}`",
        f"- Citation metadata resolution: `{'PASS' if citation_pass else 'FAIL'}`",
        f"- Adjacency bounds: `{'PASS' if adjacency_pass else 'FAIL'}`",
        f"- Source, section, and category filters: `{'PASS' if filter_pass else 'FAIL'}`",
        "",
        "## First ingestion",
        "",
        *[
            f"- `{Path(item['source']).name}`: `{item['status']}`, "
            f"{item.get('chunk_count', 0)} chunks"
            for item in first_results
        ],
        "",
        "## Second ingestion",
        "",
        *[
            f"- `{Path(item['source']).name}`: `{item['status']}`"
            for item in second_results
        ],
        "",
        "## Question results",
        "",
    ]
    for index, (question, expected, rank, section_hit, results) in enumerate(
        retrieval_rows,
        start=1,
    ):
        lines.extend(
            [
                f"### {index}. {question}",
                "",
                f"- Expected source: `{expected}`",
                f"- First expected-source rank: `{rank if rank else 'not found'}`",
                f"- Expected-section hit: `{section_hit}`",
                "- Ranked results:",
                *[
                    (
                        f"  {result_rank}. `{Path(result.source_path).name}` — "
                        f"`{result.section}` — score {result.score:.3f} — "
                        f"page {result.page_start} — chunk `{result.id}`"
                    )
                    for result_rank, result in enumerate(results, start=1)
                ],
                "",
            ]
        )

    lines.extend(
        [
            "## Unsupported-question retrieval observations",
            "",
            "Related chunks may be returned; the domain agent must still inspect full",
            "evidence and return `INSUFFICIENT_EVIDENCE` when it does not support the",
            "challenge-specific claim.",
            "",
        ]
    )
    for question, results in unsupported_results:
        lines.extend(
            [
                f"### {question}",
                "",
                f"- Candidate count: {len(results)}",
                *[
                    (
                        f"- `{Path(result.source_path).name}` — `{result.section}` — "
                        f"score {result.score:.3f}"
                    )
                    for result in results
                ],
                "",
            ]
        )
    lines.extend(["## Adjacency checks", "", *adjacency_notes, ""])
    lines.extend(
        [
            "## Filter checks",
            "",
            f"- Source filter: `{len(source_filtered)}` matching results",
            f"- Section filter: `{len(section_filtered)}` matching results",
            f"- Paper-category filter: `{len(category_filtered)}` matching results",
            f"- Result: `{'PASS' if filter_pass else 'FAIL'}`",
            "",
        ]
    )
    (OUTPUT / "retrieval_evaluation.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    log_lines = [
        "XCT CORE OFFLINE DOMAIN-RAG EVALUATION",
        f"DATABASE={DATABASE}",
        f"RETRIEVAL_PROVIDER={EMBEDDING_PROVIDER}",
        f"EMBEDDING_MODEL={EMBEDDING_MODEL}",
        "OPENAI_EMBEDDINGS_USED=False",
        f"EXTRACTION={'PASS' if extraction_pass else 'FAIL'}",
        f"RECALL_AT_5={recall:.3f}",
        f"MRR={mrr:.3f}",
        f"SECTION_ACCURACY={section_accuracy:.3f}",
        f"UNCHANGED_REINGESTION={'PASS' if unchanged_pass else 'FAIL'}",
        f"CITATION_METADATA={'PASS' if citation_pass else 'FAIL'}",
        f"ADJACENCY={'PASS' if adjacency_pass else 'FAIL'}",
        f"FILTERS={'PASS' if filter_pass else 'FAIL'}",
        f"OVERALL={'PASS' if overall else 'FAIL'}",
        "API_KEY_REQUIRED=False",
    ]
    (OUTPUT / "execution_log.txt").write_text(
        "\n".join(log_lines) + "\n",
        encoding="utf-8",
    )
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())

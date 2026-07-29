from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .config import CHUNK_OVERLAP_CHARS, MAX_CHUNK_CHARS
from .models import Chunk, LoadedUnit

_NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s+[A-Z][^.!?]{1,120}$")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+)$")
_CITATION_LINE = re.compile(r"^\s*(?:\[\d+\]|\(\d{4}\)|doi\b)", re.IGNORECASE)
_ROMAN_FRAGMENT = re.compile(r"^([IVXLC]+)[.)]\s+([A-Z])$")
_PAGE_OR_JOURNAL_LINE = re.compile(
    r"(?:\bvol\.?\s*\d+|\bpp?\.?\s*\d+|"
    r"\b(?:journal|transactions|proceedings|symposium|conference)\b)",
    re.IGNORECASE,
)
_COMMON_PAPER_HEADINGS = {
    "abstract", "introduction", "background", "methods", "methodology",
    "results", "discussion", "conclusion", "conclusions", "references",
    "acknowledgments", "appendix", "limitations", "evaluation",
}
_CANONICAL_HEADINGS = {
    "ABSTRACT": "Abstract",
    "INTRODUCTION": "Introduction",
    "RELATEDWORK": "Related Work",
    "BACKGROUND": "Background",
    "DATASETDESCRIPTION": "Dataset Description",
    "DOMAINOBJECTIVESANDCOLLABORATION": "Domain Objectives and Collaboration",
    "VISUALIZATIONDESIGNOFLATTICEANALYTICS": "Visualization Design of LatticeAnalytics",
    "IMPLEMENTATIONANDCONTAINERIZEDDEPLOYMENT": "Implementation and Containerized Deployment",
    "RESULTSANDCASESTUDIES": "Results and Case Studies",
    "USEREVALUATION": "User Evaluation",
    "DISCUSSIONANDLIMITATIONS": "Discussion and Limitations",
    "CONCLUSION": "Conclusion",
    "CONCLUSIONS": "Conclusions",
    "ACKNOWLEDGMENT": "Acknowledgment",
    "ACKNOWLEDGMENTS": "Acknowledgments",
    "NEWPERSPECTIVES": "New Perspectives",
    "REFERENCES": "References",
}


@dataclass(slots=True)
class _SectionBlock:
    section: str
    text: str
    page: int | None
    metadata: dict


def _looks_like_heading(line: str, *, allow_titlecase: bool = True) -> bool:
    candidate = " ".join(line.strip().split())
    if not candidate or len(candidate) > 140:
        return False
    if (
        _CITATION_LINE.match(candidate)
        or candidate.startswith(("(", "["))
        or candidate.endswith((",", ";", "-", "–"))
        or "@" in candidate
        or candidate.count(",") >= 2
        or _PAGE_OR_JOURNAL_LINE.search(candidate)
    ):
        return False
    if _MARKDOWN_HEADING.match(candidate) or _NUMBERED_HEADING.match(candidate):
        return True
    words = candidate.split()
    if candidate.lower() in _COMMON_PAPER_HEADINGS:
        return True
    compact = re.sub(r"[^A-Za-z]", "", candidate).upper()
    if (
        (3 <= len(words) <= 12 or compact in _CANONICAL_HEADINGS)
        and candidate.isupper()
        and any(char.isalpha() for char in candidate)
        and not candidate.endswith((".", ":", "?", "!"))
    ):
        return True
    if (
        allow_titlecase
        and 2 <= len(words) <= 10
        and candidate == candidate.title()
        and not candidate.endswith((".", "?", "!", ":"))
        and not any(char.isdigit() for char in candidate)
    ):
        return True
    return False


def _clean_heading(line: str) -> str:
    match = _MARKDOWN_HEADING.match(line.strip())
    candidate = (match.group(1) if match else line).strip()
    numbered_with_description = re.match(
        r"^((?:\d+(?:\.\d+)*|[A-Z])[.)])\s*([^:]+):\s+.+$",
        candidate,
    )
    if numbered_with_description:
        candidate = (
            f"{numbered_with_description.group(1)} "
            f"{numbered_with_description.group(2).strip()}"
        )
    roman = re.match(r"^([IVXLC]+)\s*[.)]\s*(.+)$", candidate)
    prefix = f"{roman.group(1)}. " if roman else ""
    body = roman.group(2) if roman else candidate
    compact = re.sub(r"[^A-Za-z]", "", body).upper()
    canonical = _CANONICAL_HEADINGS.get(compact)
    return f"{prefix}{canonical}".strip() if canonical else candidate


def _logical_lines(text: str) -> list[str]:
    """Join IEEE Roman-numeral heading fragments split across extracted lines."""
    raw = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(raw):
        line = raw[index].strip()
        fragment = _ROMAN_FRAGMENT.match(line)
        if fragment and index + 1 < len(raw):
            following = " ".join(raw[index + 1].strip().split())
            if (
                following
                and len(following) <= 100
                and following.isupper()
                and not _CITATION_LINE.match(following)
            ):
                line = f"{fragment.group(1)}. {fragment.group(2)}{following}"
                index += 1
        output.append(line)
        index += 1
    return output


def _heading_level(line: str) -> int:
    candidate = line.strip()
    markdown = re.match(r"^(#{1,6})\s+", candidate)
    if markdown:
        return len(markdown.group(1))
    numbered = re.match(r"^(\d+(?:\.\d+)*)[.)]?\s+", candidate)
    if numbered:
        return numbered.group(1).count(".") + 1
    return 1


def _section_blocks(units: list[LoadedUnit]) -> list[_SectionBlock]:
    blocks: list[_SectionBlock] = []
    current_section = "Document overview"
    heading_path: list[str] = []
    in_references = False
    for unit in units:
        if unit.metadata.get("kind") == "dataset_overview":
            blocks.append(_SectionBlock("Dataset overview", unit.text.strip(), unit.page, unit.metadata))
            continue
        if unit.metadata.get("kind") == "dataset_rows":
            row_start = unit.metadata.get("row_start")
            row_end = unit.metadata.get("row_end")
            blocks.append(_SectionBlock(f"Dataset rows {row_start}-{row_end}", unit.text.strip(), unit.page, unit.metadata))
            continue

        buffer: list[str] = []
        for raw_line in _logical_lines(unit.text):
            line = raw_line.strip()
            if not in_references and _looks_like_heading(
                line,
                allow_titlecase=unit.metadata.get("kind") != "paper",
            ):
                if buffer:
                    blocks.append(_SectionBlock(current_section, "\n".join(buffer).strip(), unit.page, unit.metadata))
                    buffer = []
                heading = _clean_heading(line)
                level = _heading_level(line)
                heading_path = heading_path[: max(0, level - 1)]
                heading_path.append(heading)
                current_section = " > ".join(heading_path)
                if re.sub(r"[^a-z]", "", heading.lower()).endswith("references"):
                    in_references = True
            elif line:
                buffer.append(line)
            elif buffer and buffer[-1] != "":
                buffer.append("")
        if buffer:
            blocks.append(_SectionBlock(current_section, "\n".join(buffer).strip(), unit.page, unit.metadata))
    return [block for block in blocks if block.text]


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + max_chars)
                if end < len(paragraph):
                    boundary = paragraph.rfind(" ", start, end)
                    if boundary > start + max_chars // 2:
                        end = boundary
                piece = paragraph[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= len(paragraph):
                    break
                safe_overlap = min(max(overlap_chars, 0), max_chars // 2)
                start = max(end - safe_overlap, start + 1)
            continue

        proposed = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(proposed) <= max_chars:
            current = proposed
            continue

        if current:
            chunks.append(current.strip())
            available_overlap = max(0, max_chars - len(paragraph) - 2)
            safe_overlap = min(max(overlap_chars, 0), available_overlap)
            tail = current[-safe_overlap:].strip() if safe_overlap else ""
            current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
        else:
            current = paragraph

    if current:
        chunks.append(current.strip())
    return chunks


def build_chunks(units: list[LoadedUnit]) -> list[Chunk]:
    if not units:
        return []
    source_path = units[0].source_path
    title = units[0].title
    document_id = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:20]
    blocks = _section_blocks(units)
    chunks: list[Chunk] = []

    for block in blocks:
        pieces = _split_long_text(block.text, MAX_CHUNK_CHARS, CHUNK_OVERLAP_CHARS)
        for piece in pieces:
            index = len(chunks)
            digest_input = f"{source_path}\n{block.section}\n{index}\n{piece}".encode("utf-8")
            chunk_id = hashlib.sha256(digest_input).hexdigest()[:24]
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    source_path=source_path,
                    title=title,
                    section=block.section,
                    page_start=block.page,
                    page_end=block.page,
                    chunk_index=index,
                    text=piece,
                    source_category=(
                        "dataset"
                        if str(block.metadata.get("kind", "")).startswith("dataset")
                        else "paper"
                        if block.metadata.get("kind") == "paper"
                        else "document"
                    ),
                    metadata=dict(block.metadata),
                )
            )
    for index, chunk in enumerate(chunks):
        chunk.previous_chunk_id = chunks[index - 1].id if index > 0 else None
        chunk.next_chunk_id = chunks[index + 1].id if index + 1 < len(chunks) else None
        chunk.metadata["section_path"] = chunk.section
        chunk.metadata["section_chunk_index"] = sum(
            1 for prior in chunks[:index] if prior.section == chunk.section
        )
    return chunks

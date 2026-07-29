from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd
from pypdf import PdfReader

from .models import LoadedUnit

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".csv", ".tsv", ".json", ".jsonl", ".xlsx"}

_PDF_FURNITURE = (
    re.compile(r"^\d+\s+IEEE TRANSACTIONS\b", re.IGNORECASE),
    re.compile(r"^[A-Z][A-Z\s]+et al\.\s*:", re.IGNORECASE),
    re.compile(r"^AMERICAN SOCIETY FOR PRECISION ENGINEERING\s+\d+$", re.IGNORECASE),
    re.compile(r"^Authorized licensed use limited to:", re.IGNORECASE),
    re.compile(r"^Downloaded on .* Restrictions apply\.$", re.IGNORECASE),
    re.compile(r"^\s*\d{3,5}\s*$"),
)


def discover_files(path: str | Path) -> list[Path]:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported file type: {target.suffix}")
        return [target]
    return sorted(
        item for item in target.rglob("*")
        if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
    )


def load_file(path: str | Path) -> list[LoadedUnit]:
    source = Path(path).expanduser().resolve()
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(source)
    if suffix in {".txt", ".md"}:
        return _load_text(source)
    if suffix in {".csv", ".tsv", ".xlsx"}:
        return _load_table(source)
    if suffix in {".json", ".jsonl"}:
        return _load_json(source)
    raise ValueError(f"Unsupported file type: {suffix}")


def _load_pdf(path: Path) -> list[LoadedUnit]:
    reader = PdfReader(str(path))
    title = str((reader.metadata or {}).get("/Title") or path.stem)
    units: list[LoadedUnit] = []
    empty_pages: list[int] = []
    characters_per_page: list[int] = []
    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        retained_lines = [
            line
            for line in raw_text.splitlines()
            if not any(pattern.search(line.strip()) for pattern in _PDF_FURNITURE)
        ]
        text = "\n".join(retained_lines).strip()
        characters_per_page.append(len(text))
        if not text:
            empty_pages.append(page_number)
            continue
        units.append(
            LoadedUnit(
                text=text,
                title=title,
                source_path=str(path),
                page=page_number,
                metadata={"kind": "paper", "file_type": "pdf"},
            )
        )
    diagnostics = {
        "total_pages": len(reader.pages),
        "pages_with_text": len(units),
        "empty_pages": empty_pages,
        "characters_per_page": characters_per_page,
        "extraction_status": (
            "OCR_REQUIRED"
            if reader.pages and not units
            else "EXTRACTION_INCOMPLETE"
            if empty_pages
            else "ok"
        ),
        "extraction_warnings": (
            ["No extractable text was found; the PDF may require OCR."]
            if reader.pages and not units
            else [f"{len(empty_pages)} page(s) contained no extractable text."]
            if empty_pages
            else []
        ),
    }
    for unit in units:
        unit.metadata["extraction_diagnostics"] = diagnostics
    return units


def _load_text(path: Path) -> list[LoadedUnit]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        LoadedUnit(
            text=text,
            title=path.stem,
            source_path=str(path),
            metadata={"kind": "document", "file_type": path.suffix.lower().lstrip(".")},
        )
    ]


def _load_table(path: Path) -> list[LoadedUnit]:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    elif path.suffix.lower() == ".tsv":
        frame = pd.read_csv(path, sep="\t")
    else:
        frame = pd.read_excel(path)

    frame.columns = [str(column) for column in frame.columns]
    units = [_table_overview(path, frame)]
    batch_size = 25
    for start in range(0, len(frame), batch_size):
        batch = frame.iloc[start:start + batch_size]
        text = batch.to_json(orient="records", date_format="iso", force_ascii=False)
        units.append(
            LoadedUnit(
                text=f"Dataset rows {start} through {start + len(batch) - 1}:\n{text}",
                title=path.stem,
                source_path=str(path),
                metadata={
                    "kind": "dataset_rows",
                    "file_type": path.suffix.lower().lstrip("."),
                    "row_start": start,
                    "row_end": start + len(batch) - 1,
                },
            )
        )
    return units


def _table_overview(path: Path, frame: pd.DataFrame) -> LoadedUnit:
    lines = [
        "Dataset overview",
        f"Rows: {len(frame)}",
        f"Columns: {len(frame.columns)}",
        "Schema:",
    ]
    for column in frame.columns:
        series = frame[column]
        missing = int(series.isna().sum())
        lines.append(f"- {column}: dtype={series.dtype}, missing={missing}")
        if pd.api.types.is_numeric_dtype(series):
            clean = pd.to_numeric(series, errors="coerce").dropna()
            if not clean.empty:
                lines.append(
                    "  numeric_summary="
                    f"min:{clean.min()}, max:{clean.max()}, mean:{clean.mean()}, "
                    f"median:{clean.median()}, std:{clean.std(ddof=0)}"
                )
        else:
            values = series.dropna().astype(str).value_counts().head(5)
            if not values.empty:
                top = ", ".join(f"{key} ({count})" for key, count in values.items())
                lines.append(f"  top_values={top}")
    sample = frame.head(5).to_json(orient="records", date_format="iso", force_ascii=False)
    lines.extend(["Sample rows:", sample])
    return LoadedUnit(
        text="\n".join(lines),
        title=path.stem,
        source_path=str(path),
        metadata={"kind": "dataset_overview", "file_type": path.suffix.lower().lstrip(".")},
    )


def _load_json(path: Path) -> list[LoadedUnit]:
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else [payload]

    if records and all(isinstance(item, dict) for item in records):
        frame = pd.json_normalize(records)
        return [_table_overview(path, frame), *_json_record_batches(path, records)]

    return [
        LoadedUnit(
            text=json.dumps(records, indent=2, ensure_ascii=False, default=str),
            title=path.stem,
            source_path=str(path),
            metadata={"kind": "document", "file_type": path.suffix.lower().lstrip(".")},
        )
    ]


def _json_record_batches(path: Path, records: list[dict[str, Any]]) -> Iterable[LoadedUnit]:
    batch_size = 25
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        yield LoadedUnit(
            text=(
                f"JSON records {start} through {start + len(batch) - 1}:\n"
                + json.dumps(batch, ensure_ascii=False, default=str)
            ),
            title=path.stem,
            source_path=str(path),
            metadata={
                "kind": "dataset_rows",
                "file_type": path.suffix.lower().lstrip("."),
                "row_start": start,
                "row_end": start + len(batch) - 1,
            },
        )

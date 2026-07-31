from pathlib import Path

def extract_paper(path: str | Path, pages: list[int] | None = None, keywords: list[str] | None = None, maximum_excerpt_characters: int = 12000) -> dict:
    p=Path(path)
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e: raise RuntimeError("PDF extraction requires pypdf; no package was installed") from e
        chunks=[f"page {i+1}: {page.extract_text() or ''}" for i,page in enumerate(PdfReader(p).pages) if not pages or i+1 in pages]
    else: chunks=[f"text: {p.read_text(encoding='utf-8')}"]
    text="\n".join(chunks)
    if keywords: text="\n".join(line for line in text.splitlines() if any(k.lower() in line.lower() for k in keywords)) or text
    return {"title":p.stem,"excerpts":text[:maximum_excerpt_characters],"source":str(p),"pages":pages or []}

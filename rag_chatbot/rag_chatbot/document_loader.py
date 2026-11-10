"""
document_loader.py - Finds the document (PDF or TXT) and loads its text.

Put your file inside the data/ folder. The first .pdf or .txt file found is used,
or set DOCUMENT_PATH in the .env file to choose a specific file.
"""
import hashlib
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

import config

SUPPORTED = (".pdf", ".txt")
PAGE_MARKER = re.compile(r"^\s*Page \d+ of \d+\s*$", re.MULTILINE)

# Characters that PDF-to-text tools often produce and that break keyword search.
_CHAR_FIXES = {
    "­": "-",   # soft hyphen
    ";": ";",   # Greek question mark that looks like ';'
    "“": '"', "”": '"',
    "‘": "'", "’": "'",
}


class DocumentError(Exception):
    """A problem with the document that we can explain to the user."""


def locate_document():
    """Return (path, sha256_hash) of the document to use.

    The hash lets us skip re-chunking and re-embedding when the file did not change.
    """
    if config.DOCUMENT_PATH:
        path = Path(config.DOCUMENT_PATH).expanduser()
        if not path.is_absolute():
            path = config.BASE_DIR / path
        if not path.is_file():
            raise DocumentError(f"Document not found at: {path}")
    else:
        config.DATA_DIR.mkdir(exist_ok=True)
        files = sorted(p for p in config.DATA_DIR.iterdir() if p.suffix.lower() in SUPPORTED)
        if not files:
            raise DocumentError(
                "No document found. Put a .pdf or .txt file inside the 'data' folder and restart the app."
            )
        path = files[0]

    if path.suffix.lower() not in SUPPORTED:
        raise DocumentError("Unsupported file type. Please use a .pdf or .txt file.")

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return path, digest.hexdigest()


def _clean(text):
    for bad, good in _CHAR_FIXES.items():
        text = text.replace(bad, good)
    return text


def _strip_contents(raw):
    """Drop a leading table of contents.

    A contents list only holds short section titles (no answers) and would crowd out the real
    text during search. The body is taken to start at the first all-caps 'THE ...' title line
    that follows the 'CONTENTS' heading.
    """
    head = raw[:600]
    m = re.search(r"^\s*CONTENTS\s*$", head, re.MULTILINE)
    if not m:
        return raw
    body = re.search(r"^THE [A-Z ,]+$", raw[m.end():], re.MULTILINE)
    if not body:
        return raw
    return raw[: m.start()] + raw[m.end() + body.start():]


def _load_txt(path):
    """Read a text file; split it into 'pages' wherever a 'Page N of M' marker appears."""
    raw = _strip_contents(_clean(path.read_text(encoding="utf-8", errors="ignore")))
    parts = PAGE_MARKER.split(raw)
    return [
        Document(page_content=part.strip(), metadata={"page": i + 1})
        for i, part in enumerate(parts)
        if part.strip()
    ]


def _load_pdf(path):
    try:
        pages = PyPDFLoader(str(path)).load()
    except Exception as e:
        raise DocumentError(f"Could not read the PDF ({type(e).__name__}).") from None
    for p in pages:
        p.page_content = _clean(p.page_content)
    return pages


def load_document(path):
    """Read the file. Returns (pages, full_text)."""
    pages = _load_txt(path) if path.suffix.lower() == ".txt" else _load_pdf(path)
    full_text = "\n".join(p.page_content for p in pages).strip()
    if len(full_text) < 50:
        raise DocumentError(
            "This document has no selectable text (a scanned PDF?). Please use a text-based file."
        )
    return pages, full_text

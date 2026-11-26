"""Reads the text of each page of a PDF. The only place that talks to pypdf.

pypdf is imported inside the function, so the rest of the app still runs without it.
"""

import re
from collections import Counter
from io import BytesIO

PDF_SIGNATURE = b"%PDF-"
MAX_PAGE_CHARS = 20_000
# "12", "Page 3", "3 / 40", "page 3 of 40", "صفحة 3", "3 من 40"
PAGE_NUMBER = re.compile(
    r"^(?:page|صفحة|ص)?\s*[\d٠-٩]{1,4}(?:\s*(?:/|of|من)\s*[\d٠-٩]{1,4})?$", re.IGNORECASE
)
DIGITS = re.compile(r"[\d٠-٩]+")
# A line seen at the top or bottom of this share of pages is a running header or footer.
REPEATED_SHARE = 0.6
EDGE_LINES = 2


class PdfTextError(ValueError):
    """The file can't be used. `code` says why, for the teacher's message."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class PdfReaderUnavailable(RuntimeError):
    """pypdf isn't installed on this machine."""


def read_pdf_pages(data: bytes, *, max_pages: int) -> list[str]:
    """The cleaned text of every page. Raises PdfTextError for a file that can't be used."""
    # The signature may follow a few bytes of junk, which readers accept.
    if PDF_SIGNATURE not in data[:1024]:
        raise PdfTextError("not_pdf", "This file is not a PDF.")

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise PdfReaderUnavailable("pypdf is not installed.") from error

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not _opens_without_password(reader):
            raise PdfTextError("pdf_locked", "This PDF is locked with a password.")
        page_count = len(reader.pages)
        if page_count > max_pages:
            raise PdfTextError("pdf_too_many_pages", f"This PDF has more than {max_pages} pages.")
        raw_pages = [page.extract_text() or "" for page in reader.pages]
    except PdfTextError:
        raise
    # pypdf raises many kinds of errors for a broken file; each one means the same here.
    except Exception as error:
        raise PdfTextError("pdf_unreadable", "This PDF can't be read.") from error

    if page_count == 0:
        raise PdfTextError("pdf_unreadable", "This PDF has no pages.")

    pages = clean_pages(raw_pages)
    if not any(pages):
        raise PdfTextError("pdf_no_text", "No text was found. It may be a scanned PDF.")
    return pages


def _opens_without_password(reader):
    # Many PDFs are "encrypted" only to stop printing or copying, with an empty password.
    try:
        return bool(reader.decrypt(""))
    except Exception:
        return False


def clean_pages(raw_pages: list[str]) -> list[str]:
    """Removes page numbers, running headers and footers, and extra spaces."""
    pages = []
    for raw in raw_pages:
        # PostgreSQL can't store a NUL character in JSON.
        lines = (" ".join(line.split()) for line in raw.replace("\x00", "").splitlines())
        pages.append([line for line in lines if line and not PAGE_NUMBER.match(line)])

    repeated = _running_lines(pages)
    cleaned = []
    for lines in pages:
        kept = [
            line
            for index, line in enumerate(lines)
            if not (_is_edge(index, len(lines)) and _shape(line) in repeated)
        ]
        cleaned.append("\n".join(kept)[:MAX_PAGE_CHARS])
    return cleaned


def _shape(line):
    """The line with its numbers removed, so "Chapter 2 - page 7" matches on every page."""
    return DIGITS.sub("#", line.casefold())


def _is_edge(index, total):
    return index < EDGE_LINES or index >= total - EDGE_LINES


def _running_lines(pages):
    if len(pages) < 3:
        return set()
    seen = Counter()
    for lines in pages:
        edges = {_shape(line) for index, line in enumerate(lines) if _is_edge(index, len(lines))}
        seen.update(edges)
    return {line for line, count in seen.items() if count >= len(pages) * REPEATED_SHARE}

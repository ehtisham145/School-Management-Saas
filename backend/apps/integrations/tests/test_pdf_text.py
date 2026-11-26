"""Reading the text of real PDF files with pypdf."""

from io import BytesIO

import pytest

from apps.integrations.pdf.text_extractor import PdfTextError, clean_pages, read_pdf_pages

pypdf = pytest.importorskip("pypdf")


def _pdf(*pages):
    """A small, valid PDF with one line of Helvetica text per item, built by hand."""
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    kids = []
    next_id = 4
    for lines in pages:
        page_id, content_id = next_id, next_id + 1
        next_id += 2
        kids.append(page_id)
        commands = ["BT", "/F1 12 Tf", "14 TL", "72 720 Td"]
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        objects[content_id] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % content_id
        )
    references = " ".join(f"{kid} 0 R" for kid in kids)
    objects[2] = f"<< /Type /Pages /Kids [{references}] /Count {len(kids)} >>".encode()

    output = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in range(1, next_id):
        offsets[number] = len(output)
        output += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    start = len(output)
    output += b"xref\n0 %d\n0000000000 65535 f \n" % next_id
    for number in range(1, next_id):
        output += b"%010d 00000 n \n" % offsets[number]
    output += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (next_id, start)
    return bytes(output)


def _blank_pdf(pages, password=None):
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    if password:
        writer.encrypt(password, algorithm="RC4-128")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_the_text_of_each_page_is_read():
    data = _pdf(["Plants make food.", "They need light."], ["Cells respire."])

    pages = read_pdf_pages(data, max_pages=10)

    assert len(pages) == 2
    assert "Plants make food." in pages[0]
    assert "They need light." in pages[0]
    assert pages[1] == "Cells respire."


def test_page_numbers_and_running_headers_are_removed():
    topics = ["Plants make food.", "Cells respire.", "Water evaporates."]
    pages = [
        ["Biology Grade 7", topic, f"Page {index} of 3"]
        for index, topic in enumerate(topics, start=1)
    ]

    text = read_pdf_pages(_pdf(*pages), max_pages=10)

    assert text == topics


def test_a_file_that_is_not_a_pdf_is_refused():
    with pytest.raises(PdfTextError) as error:
        read_pdf_pages(b"PK\x03\x04 a Word file", max_pages=10)

    assert error.value.code == "not_pdf"


def test_a_broken_pdf_is_refused():
    with pytest.raises(PdfTextError) as error:
        read_pdf_pages(b"%PDF-1.4\nthis is not really a pdf", max_pages=10)

    assert error.value.code == "pdf_unreadable"


def test_a_pdf_with_too_many_pages_is_refused():
    with pytest.raises(PdfTextError) as error:
        read_pdf_pages(_blank_pdf(4), max_pages=3)

    assert error.value.code == "pdf_too_many_pages"


def test_a_pdf_with_no_text_says_so():
    with pytest.raises(PdfTextError) as error:
        read_pdf_pages(_blank_pdf(2), max_pages=10)

    assert error.value.code == "pdf_no_text"


def test_a_password_locked_pdf_is_refused():
    with pytest.raises(PdfTextError) as error:
        read_pdf_pages(_blank_pdf(1, password="secret"), max_pages=10)

    assert error.value.code == "pdf_locked"


def test_cleaning_removes_nul_characters_and_extra_spaces():
    assert clean_pages(["Plants\x00   make    food.\n\n  12  \n"]) == ["Plants make food."]


def test_a_short_pdf_keeps_lines_that_repeat():
    # With fewer than three pages, nothing counts as a running header.
    pages = ["Same line\nOne", "Same line\nTwo"]

    assert clean_pages(pages) == pages

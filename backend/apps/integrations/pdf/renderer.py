"""HTML to PDF. The only place that talks to WeasyPrint.

WeasyPrint needs the Pango libraries. The Docker image and CI install them; a Windows
machine needs GTK. Without them, html_to_pdf() raises PdfUnavailable and the rest of
the app keeps working.
"""

from django.conf import settings


class PdfUnavailable(RuntimeError):
    """The PDF libraries aren't installed on this machine."""


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        raise PdfUnavailable(
            "WeasyPrint can't load. Install Pango (see docs/development.md)."
        ) from exc

    return HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()

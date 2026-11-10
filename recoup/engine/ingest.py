"""Extraction paths and failure statuses; design/02 §5.8."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from recoup.contracts.interfaces import IngestOutput
from recoup.engine.scans import ScanUnavailable, image_text, ocr_available, pdf_page_text


class Ingestor:
    def __init__(self, *, vision_llm=None):
        self.vision_llm = vision_llm

    def ingest(self, doc, bundle_dir=None) -> IngestOutput:
        def fail(reason):
            return IngestOutput(
                text="", fields={}, field_trust={}, readable=False, method="none", failure=reason
            )

        text, method = doc.text, "structured" if doc.fields else "text"
        if doc.file:
            if bundle_dir is None:
                return fail("corrupt")
            root = Path(bundle_dir).resolve()
            path = (root / doc.file).resolve()
            if not path.is_relative_to(root):
                return fail("unsupported")
            try:
                data = path.read_bytes()
            except OSError:
                return fail("corrupt")
            if data.startswith(b"%PDF-"):
                try:
                    reader = PdfReader(BytesIO(data))
                    if reader.is_encrypted:
                        return fail("encrypted")
                    pages = [page.extract_text() or "" for page in reader.pages]
                except (PdfReadError, ValueError, OSError, KeyError, IndexError):
                    return fail("corrupt")
                method = "text_pdf"
                if any(not page.strip() for page in pages):
                    if not ocr_available():
                        return fail("ocr_unavailable")
                    try:
                        pages = [
                            page if page.strip() else pdf_page_text(data, i)
                            for i, page in enumerate(pages, 1)
                        ]
                    except ScanUnavailable:
                        return fail("ocr_unavailable")
                    except (OSError, ValueError):
                        return fail("corrupt")
                    method = "ocr"
                text = "\f".join(pages)
            elif data.startswith(
                (
                    b"\x89PNG\r\n\x1a\n",
                    b"\xff\xd8\xff",
                    b"GIF87a",
                    b"GIF89a",
                    b"II*\x00",
                    b"MM\x00*",
                    b"BM",
                )
            ):
                vision = self.vision_llm
                if vision is None and not ocr_available():
                    return fail("ocr_unavailable")
                try:
                    text = image_text(data, vision_llm=vision)
                except (ImportError, ScanUnavailable):
                    return fail("ocr_unavailable")
                except (OSError, ValueError):
                    return fail("corrupt")
                method = "vision" if vision is not None else "ocr"
            elif path.suffix.lower() in {".txt", ".eml"}:
                try:
                    text = data.decode("utf-8")
                except UnicodeError:
                    return fail("corrupt")
                method = "text"
            elif path.suffix.lower() == ".pdf":
                return fail("corrupt")
            else:
                return fail("unsupported")
        if not text.strip() and (method in {"ocr", "vision"} or not doc.fields):
            return fail("empty_text")
        return IngestOutput(
            text=text,
            fields=doc.fields.copy(),
            field_trust={
                key: method if method in {"ocr", "vision"} else "source" for key in doc.fields
            },
            readable=True,
            method=method,
        )

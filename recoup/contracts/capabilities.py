"""Shared local capability probe; design/02 §5.8. No provider or database construction."""

import importlib
import os
import shutil


def scan_capabilities(*, llm_mode: str = "fake", vision: bool = False) -> dict[str, bool | str]:
    def available(load):
        try:
            load()
            return True
        except (ImportError, OSError):
            return False

    return {
        "pypdf": available(lambda: importlib.import_module("pypdf")),
        "pillow": available(lambda: importlib.import_module("PIL.Image")),
        "tesseract": shutil.which("tesseract") is not None,
        "pytesseract": available(lambda: importlib.import_module("pytesseract")),
        "pdf_renderer": shutil.which("pdftoppm") is not None,
        "vision": bool(vision and llm_mode == "live" and os.environ.get("OPENAI_API_KEY")),
        "llm_mode": llm_mode,
    }

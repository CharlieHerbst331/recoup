"""Local probes describe prerequisites without constructing a provider (§5.8)."""

import pytest

from recoup.contracts import capabilities


@pytest.mark.parametrize(
    "mode,requested,key,expected",
    [
        ("fake", True, "secret", False),
        ("replay", True, "secret", False),
        ("live", False, "secret", False),
        ("live", True, "", False),
        ("live", True, "secret", True),
    ],
)
def test_prerequisites_and_vision_mode(monkeypatch, mode, requested, key, expected):
    monkeypatch.setenv("OPENAI_API_KEY", key)
    monkeypatch.setattr(capabilities.importlib, "import_module", lambda name: object())
    monkeypatch.setattr(capabilities.shutil, "which", lambda name: "/synthetic/bin/" + name)
    report = capabilities.scan_capabilities(llm_mode=mode, vision=requested)
    assert report == {
        "pypdf": True,
        "pillow": True,
        "pytesseract": True,
        "tesseract": True,
        "pdf_renderer": True,
        "vision": expected,
        "llm_mode": mode,
    }
    assert "secret" not in str(report)


def test_missing_and_unloadable_optional_backends(monkeypatch):
    def unavailable(name):
        if name == "pypdf":
            raise ImportError("optional package absent")
        raise OSError("optional native library absent")

    monkeypatch.setattr(capabilities.importlib, "import_module", unavailable)
    monkeypatch.setattr(capabilities.shutil, "which", lambda name: None)
    report = capabilities.scan_capabilities()
    assert report["llm_mode"] == "fake"
    assert not any(value for key, value in report.items() if key != "llm_mode")

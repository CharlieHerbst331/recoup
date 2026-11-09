"""SYNTHETIC scan unit lane; real OCR checks require optional installed tools."""

import base64
from io import BytesIO
from types import SimpleNamespace as NS

import pytest

from recoup.contracts.interfaces import LLMResponse
from recoup.engine import scans
from recoup.engine.factory import build_engine
from recoup.engine.ingest import Ingestor
from recoup.engine.llm.openai_compat import OpenAICompatLLM
from recoup.engine.llm.replay import ReplayLLM
from recoup.engine.tools import ToolSessionFactory

from .fixtures import fact_inputs
from .test_harness_factory_ingest import doc, write_pdf
from .test_openai_compat import StubClient, completion
from .tool_support import ToolWorld


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden in scan tests")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


def image_bytes(text="SYNTHETIC RECEIVED 360"):
    Image = pytest.importorskip("PIL.Image")
    ImageDraw = pytest.importorskip("PIL.ImageDraw")
    ImageFont = pytest.importorskip("PIL.ImageFont")
    image = Image.new("RGB", (1000, 160), "white")
    ImageDraw.Draw(image).text((20, 40), text, fill="black", font=ImageFont.load_default(size=40))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def ingest_image(tmp_path, ingestor=None, **kwargs):
    (tmp_path / "scan.bin").write_bytes(image_bytes())
    return (ingestor or Ingestor()).ingest(doc(file="scan.bin", **kwargs), str(tmp_path))


def test_ocr_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: False)
    (tmp_path / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\nSYNTHETIC")
    output = Ingestor().ingest(doc(file="scan.png", fields={"signed": True}), str(tmp_path))
    assert not output.readable and output.failure == "ocr_unavailable"
    assert output.method == "none" and output.fields == {} and output.field_trust == {}
    path = tmp_path / "scan.pdf"
    write_pdf(path, text=False)
    assert Ingestor().ingest(doc(file=path.name), str(tmp_path)).failure == "ocr_unavailable"


def test_capability_probe_and_vision_gate(monkeypatch):
    monkeypatch.setattr(scans.shutil, "which", lambda name: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert not scans.ocr_available()
    assert not scans.scan_capabilities(llm_mode="live", vision=True)["vision"]
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    assert scans.scan_capabilities(llm_mode="live", vision=True)["vision"]
    assert not scans.scan_capabilities(llm_mode="fake", vision=True)["vision"]
    assert not scans.scan_capabilities(llm_mode="live", vision=False)["vision"]
    original = scans.importlib.import_module

    def missing(name):
        if name == "pytesseract":
            raise ImportError("optional extra absent")
        return original(name)

    monkeypatch.setattr(scans.importlib, "import_module", missing)
    assert not scans.scan_capabilities()["pytesseract"]


@pytest.mark.parametrize("method", ["ocr", "vision"])
def test_scan_trust_reaches_actual_fact_tool(tmp_path, monkeypatch, method):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    monkeypatch.setattr("recoup.engine.ingest.image_text", lambda *a, **kw: "received 360")
    output = ingest_image(
        tmp_path,
        Ingestor(vision_llm=object() if method == "vision" else None),
        fields={"received.A": 360},
    )
    assert output.readable and output.method == method
    assert output.field_trust == {"received.A": method}
    facts, evidence, revisions = fact_inputs(
        [dict(id="scan", kind="pod", fields={})], "SYNTHETIC-SCAN"
    )
    evidence[0].text, evidence[0].method = output.text, output.method
    world = ToolWorld(facts, evidence, revisions, [], [])
    result = (
        ToolSessionFactory()
        .open(world, facts.case_id, "scan", "harness")
        .call(
            "propose_fact",
            dict(
                evidence_id=evidence[0].evidence_id,
                key="received.A",
                value=360,
                citation=dict(
                    evidence_id=evidence[0].evidence_id, locator="text", quote="received 360"
                ),
            ),
        )
    )
    assert result.ok and result.result["accepted"] and result.result["trust"] == method
    assert world.revisions[-1].trust == method


def test_pdf_missing_pages_use_ocr_in_page_order(tmp_path, monkeypatch):
    from pypdf import PdfReader, PdfWriter

    source = tmp_path / "source.pdf"
    write_pdf(source)
    reader = PdfReader(source)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_blank_page(width=200, height=200)
    writer.add_page(reader.pages[1])
    path = tmp_path / "mixed.pdf"
    writer.write(path)
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    called = []

    def extract(data, page):
        called.append(page)
        return "SYNTHETIC scanned page"

    monkeypatch.setattr("recoup.engine.ingest.pdf_page_text", extract)
    output = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert output.method == "ocr" and called == [2]
    assert output.text == "SYNTHETIC POD signed\fSYNTHETIC scanned page\freceived 360"


def test_pdf_renderer_missing_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    monkeypatch.setattr(scans.shutil, "which", lambda name: None)
    path = tmp_path / "scan.pdf"
    write_pdf(path, text=False)
    output = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert output.failure == "ocr_unavailable"


@pytest.mark.parametrize(
    "error,failure",
    [
        (scans.ScanUnavailable(), "ocr_unavailable"),
        (OSError(), "corrupt"),
        (ValueError(), "corrupt"),
    ],
)
def test_scan_backend_failures(tmp_path, monkeypatch, error, failure):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)

    def fail(*a, **kw):
        raise error

    monkeypatch.setattr("recoup.engine.ingest.image_text", fail)
    assert ingest_image(tmp_path).failure == failure


def test_empty_scan_cannot_use_supplied_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    monkeypatch.setattr("recoup.engine.ingest.image_text", lambda *a, **kw: " ")
    output = ingest_image(tmp_path, fields={"signed": True})
    assert output.failure == "empty_text" and not output.fields


def test_vision_sdk_image_request_and_exact_replay(tmp_path):
    client = StubClient(completion(text="SYNTHETIC RECEIVED 360", finish="stop"))
    llm = OpenAICompatLLM("synthetic-vision", client=client, directory=tmp_path / "recordings")
    output = ingest_image(tmp_path, Ingestor(vision_llm=llm))
    assert output.readable and output.method == "vision"
    assert output.text == "SYNTHETIC RECEIVED 360"
    request = client.requests[0]
    assert "tools" not in request
    content = request["messages"][1]["content"]
    url = content[1]["image_url"]["url"]
    assert base64.b64decode(url.split(",")[1]).startswith(b"\x89PNG")
    replay = ReplayLLM("synthetic-vision", tmp_path / "recordings")
    assert scans.image_text(image_bytes(), vision_llm=replay) == output.text
    assert len(client.requests) == 1


def test_vision_tool_calls_are_rejected(tmp_path):
    class Unexpected:
        def next(self, *args):
            return LLMResponse(
                mode="live",
                model_id="synthetic",
                text="invented",
                tool_calls=[dict(id="x", name="end", arguments={})],
            )

    assert ingest_image(tmp_path, Ingestor(vision_llm=Unexpected())).failure == "ocr_unavailable"


def test_factory_vision_requires_flag_live_and_key(monkeypatch):
    sentinel = object()
    monkeypatch.setattr("recoup.engine.factory.get_llm", lambda c: sentinel)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    pytest.importorskip("PIL.Image")
    for mode, flag, expected in [
        ("fake", True, None),
        ("live", False, None),
        ("live", True, sentinel),
    ]:
        assert build_engine(NS(llm=mode, vision=flag)).ingestor.vision_llm is expected
    monkeypatch.delenv("OPENAI_API_KEY")
    assert build_engine(NS(llm="live", vision=True)).ingestor.vision_llm is None


@pytest.mark.skipif(not scans.ocr_available(), reason="tesseract/pytesseract/Pillow unavailable")
def test_real_tesseract_image(tmp_path):
    output = ingest_image(tmp_path)
    assert output.readable and output.method == "ocr"
    assert "SYNTHETIC" in output.text and "360" in output.text


@pytest.mark.skipif(
    not scans.ocr_available() or not scans.scan_capabilities()["pdf_renderer"],
    reason="tesseract/pytesseract/Pillow or PDF renderer unavailable",
)
def test_real_scanned_pdf(tmp_path):
    from PIL import Image

    path = tmp_path / "scanned.pdf"
    with Image.open(BytesIO(image_bytes())) as image:
        image.convert("RGB").save(path, format="PDF", resolution=150)
    output = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert output.readable and output.method == "ocr"
    assert "SYNTHETIC" in output.text and "360" in output.text


def test_ocr_backend_uses_timeout_and_preserves_frame_order(monkeypatch):
    import sys

    Image = pytest.importorskip("PIL.Image")
    frames = [Image.new("RGB", (20, 20), color) for color in ["white", "black"]]
    buffer = BytesIO()
    frames[0].save(buffer, format="TIFF", save_all=True, append_images=frames[1:])
    seen = []

    def extract(image, *, timeout):
        assert timeout == 30 and image.mode == "RGB"
        seen.append(image.getpixel((0, 0)))
        return f"SYNTHETIC page {len(seen)}\n"

    monkeypatch.setitem(sys.modules, "pytesseract", NS(image_to_string=extract))
    assert scans.image_text(buffer.getvalue()) == "SYNTHETIC page 1\fSYNTHETIC page 2"
    assert seen == [(255, 255, 255), (0, 0, 0)]


@pytest.mark.parametrize("error", [RuntimeError("timeout"), OSError("binary missing")])
def test_ocr_execution_failure_is_unavailable(monkeypatch, error):
    import sys

    def fail(*a, **kw):
        raise error

    monkeypatch.setitem(sys.modules, "pytesseract", NS(image_to_string=fail))
    with pytest.raises(scans.ScanUnavailable):
        scans.image_text(image_bytes())


def test_vision_client_failure_is_unavailable(tmp_path):
    class BrokenClient:
        def next(self, *args):
            raise RuntimeError("SYNTHETIC provider failure")

    result = ingest_image(tmp_path, Ingestor(vision_llm=BrokenClient()))
    assert result.failure == "ocr_unavailable" and not result.fields


def test_invalid_image_is_corrupt_with_available_backend(tmp_path, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    (tmp_path / "broken.png").write_bytes(b"\x89PNG\r\n\x1a\nSYNTHETIC")
    assert Ingestor().ingest(doc(file="broken.png"), str(tmp_path)).failure == "corrupt"


@pytest.mark.skipif(not scans.scan_capabilities()["pdf_renderer"], reason="pdftoppm unavailable")
def test_real_pdf_renderer_with_stub_ocr(tmp_path, monkeypatch):
    import sys

    Image = pytest.importorskip("PIL.Image")
    path = tmp_path / "scan.pdf"
    with Image.open(BytesIO(image_bytes())) as image:
        image.convert("RGB").save(path, format="PDF", resolution=150)
    seen = []

    def extract(image, *, timeout):
        seen.append(image.size)
        assert image.width > 1000 and image.height > 160
        return "SYNTHETIC stub OCR"

    monkeypatch.setitem(sys.modules, "pytesseract", NS(image_to_string=extract))
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: True)
    output = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert output.readable and output.method == "ocr"
    assert output.text == "SYNTHETIC stub OCR" and len(seen) == 1


def test_pdf_renderer_failure_is_unavailable(monkeypatch):
    import subprocess

    monkeypatch.setattr(scans.shutil, "which", lambda name: "/synthetic/pdftoppm")

    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 30 and kwargs["check"]
        raise subprocess.TimeoutExpired("pdftoppm", 30)

    monkeypatch.setattr(scans.subprocess, "run", timeout)
    with pytest.raises(scans.ScanUnavailable):
        scans.pdf_page_text(b"SYNTHETIC", 2)

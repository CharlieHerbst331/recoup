"""Evidence helpers and case mutations through app-built Worlds (design/02 §6)."""

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import recoup.app as app
from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import FieldTrust, GateIssue
from recoup.contracts.testing import NullController
from recoup.ui.evidence import evidence_fields, evidence_rows, evidence_versions, inject_document


def document(**updates):
    return BundleDoc(
        doc_ref="SYNTHETIC-UI-doc",
        kind="other",
        title="SYNTHETIC UI document",
        text="SYNTHETIC text",
    ).model_copy(update=updates)


def test_evidence_versions_include_superseded_without_duplicates(service):
    first = service.add_evidence("H", document())
    second = service.add_evidence("H", document(version=2, text="SYNTHETIC correction"))
    case, history = service.world.view("H"), service.history("H")
    before = (case.model_dump_json(), history.model_dump_json())
    versions = evidence_versions(case, history)
    assert len({row.evidence_id for row in versions}) == len(versions)
    assert versions[: len(case.evidence)] == case.evidence
    rows = [row for row in evidence_rows(versions) if row["doc_ref"] == first.doc_ref]
    assert rows == [
        {
            "evidence_id": second.evidence_id,
            "doc_ref": first.doc_ref,
            "version": 2,
            "kind": "other",
            "state": "active",
            "readable": True,
            "method": "text",
            "failure": "none",
        },
        {
            "evidence_id": first.evidence_id,
            "doc_ref": first.doc_ref,
            "version": 1,
            "kind": "other",
            "state": "superseded",
            "readable": True,
            "method": "text",
            "failure": "none",
        },
    ]
    assert (case.model_dump_json(), history.model_dump_json()) == before
    assert (
        evidence_versions(
            case.model_copy(update={"evidence": []}),
            history.model_copy(update={"evidence_all": []}),
        )
        == []
    )


def test_evidence_failures_are_visible(service):
    evidence = service.add_evidence("H", document(text=""))
    row = evidence_rows([evidence])[0]
    assert row["readable"] is False
    assert row["method"] == "none"
    assert row["failure"] == "empty_text"


@pytest.fixture
def scanned_evidence(service, monkeypatch):
    ingest = service.world.ingestor.ingest

    def scanned(doc, folder):
        return ingest(doc, folder).model_copy(
            update={"field_trust": {"ocr_field": FieldTrust.ocr, "vision_field": FieldTrust.vision}}
        )

    monkeypatch.setattr(service.world.ingestor, "ingest", scanned)
    return service.add_evidence(
        "H", document(fields={"ocr_field": 123, "vision_field": True, "source_field": "original"})
    )


def test_field_rows_use_latest_revisions_and_default_source(service, scanned_evidence):
    original = scanned_evidence.model_dump_json()
    service.confirm_field(scanned_evidence.evidence_id, "ocr_field")
    service.confirm_field(scanned_evidence.evidence_id, "vision_field")
    service.confirm_field(scanned_evidence.evidence_id, "vision_field")
    assert evidence_fields(scanned_evidence, service.history("H")) == [
        {"field": "ocr_field", "value": "123", "field_trust": "human_confirmed"},
        {"field": "source_field", "value": "original", "field_trust": "source"},
        {"field": "vision_field", "value": "True", "field_trust": "human_confirmed"},
    ]
    assert scanned_evidence.model_dump_json() == original


@pytest.mark.parametrize("file", [None, "nested/evidence.txt"])
def test_injection_stages_json_and_optional_file_then_cleans_up(service, monkeypatch, file):
    doc = document(file=file)
    add = service.add_evidence
    folders = []

    def capture(case_id, staged, folder):
        root = Path(folder)
        folders.append(root)
        assert case_id == "H"
        assert BundleDoc.model_validate_json((root / "document.json").read_text()) == staged
        if file:
            assert (root / file).read_bytes() == b"SYNTHETIC upload"
        return add(case_id, staged, folder)

    monkeypatch.setattr(service, "add_evidence", capture)
    evidence = inject_document(
        service,
        "H",
        doc.model_dump_json(),
        "upload.txt" if file else None,
        b"SYNTHETIC upload" if file else None,
    )
    assert evidence.active and evidence.readable
    assert evidence.text == ("SYNTHETIC upload" if file else "SYNTHETIC text")
    assert evidence.evidence_id in {row.evidence_id for row in service.world.view("H").evidence}
    assert len(folders) == 1 and not folders[0].exists()


def test_upload_name_supplies_missing_file_and_scheduled_upload_survives(service, monkeypatch):
    add = service.add_evidence
    folders = []

    def capture(case_id, staged, folder):
        folders.append(Path(folder))
        assert staged.file == "upload.txt"
        return add(case_id, staged, folder)

    monkeypatch.setattr(service, "add_evidence", capture)
    try:
        assert (
            inject_document(
                service,
                "H",
                document(available_at_day=1).model_dump_json(),
                "upload.txt",
                b"SYNTHETIC future upload",
            )
            is None
        )
        assert (folders[0] / "upload.txt").exists()
        assert not any(
            row.doc_ref == "SYNTHETIC-UI-doc" for row in service.world.view("H").evidence
        )
        service.advance(1)
        row = next(
            row for row in service.world.view("H").evidence if row.doc_ref == "SYNTHETIC-UI-doc"
        )
        assert row.readable and row.text == "SYNTHETIC future upload"
    finally:
        for folder in folders:
            shutil.rmtree(folder)


@pytest.mark.parametrize(
    "file",
    [
        "../escape.txt",
        "/tmp/escape.txt",
        "nested/../../escape.txt",
        "..\\escape.txt",
        "C:\\escape.txt",
        ".",
        "document.json",
        "document.json/child.txt",
    ],
)
def test_injection_rejects_unsafe_upload_paths_before_mutation(service, monkeypatch, file):
    def unexpected(*args):
        pytest.fail("Invalid input must not call add_evidence")

    monkeypatch.setattr(service, "add_evidence", unexpected)
    with pytest.raises(ValueError):
        inject_document(service, "H", document(file=file).model_dump_json(), "upload.txt", b"data")


@pytest.mark.parametrize("text", ["not JSON", "{}", '{"kind":"invalid"}'])
def test_injection_rejects_invalid_bundledoc(service, text):
    before = service.history("H").model_dump_json()
    with pytest.raises(ValueError):
        inject_document(service, "H", text)
    assert service.history("H").model_dump_json() == before


def test_injection_requires_referenced_file(service):
    with pytest.raises(ValueError, match="Upload the file"):
        inject_document(service, "H", document(file="missing.txt").model_dump_json())


def case_script():
    import recoup.app as app
    from recoup.ui.case_page import render_case

    service = app.build()
    try:
        render_case(service.world.view("H"), service.history("H"), service)
    finally:
        service.world.close()


@pytest.fixture
def case_page(service, scanned_evidence, monkeypatch):
    # AppTest runs on another thread: rebuild an in-memory World from its snapshot.
    state = {"database": service.world.db.serialize()}
    real_build = app.build

    def build():
        instance = real_build(
            app.RecoupConfig(db=":memory:", llm="fake"), controller=NullController()
        )
        instance.world.db.deserialize(state["database"])
        close = instance.world.close

        def capture_and_close():
            state["history"] = instance.history("H")
            state["view"] = instance.world.view("H")
            state["database"] = instance.world.db.serialize()
            close()

        monkeypatch.setattr(instance.world, "close", capture_and_close)
        return instance

    monkeypatch.setattr(app, "build", build)
    return AppTest.from_function(case_script, default_timeout=20), state


@pytest.mark.parametrize("key", ["ocr_field", "vision_field"])
def test_confirm_calls_facade_and_reruns_with_updated_trust(case_page, scanned_evidence, key):
    page, state = case_page
    page.run()
    button_key = f"confirm:H:{scanned_evidence.evidence_id}:{key}"
    assert page.button(key=button_key).label == "Confirm"
    page.button(key=button_key).click().run()
    assert not page.exception and not page.error
    assert button_key not in [button.key for button in page.button]
    assert state["history"].facts[-1].key == key
    assert state["history"].facts[-1].trust == "human_confirmed"
    assert any(
        {
            "field": key,
            "value": "123" if key == "ocr_field" else "True",
            "field_trust": "human_confirmed",
        }
        in table.value.to_dict("records")
        for table in page.dataframe
    )


def test_inject_form_adds_evidence_and_refreshes_pane(case_page):
    page, state = case_page
    page.run()
    page.text_area(key="document-json:H").set_value(document(version=2).model_dump_json())
    next(button for button in page.button if button.label == "Inject document").click().run()
    assert not page.exception and not page.error
    assert any(
        row.doc_ref == "SYNTHETIC-UI-doc" and row.version == 2 for row in state["view"].evidence
    )
    assert any("SYNTHETIC-UI-doc v2" in item.value for item in page.text)


def test_invalid_form_json_displays_error_without_traceback(case_page):
    page, _ = case_page
    page.run()
    page.text_area(key="document-json:H").set_value("invalid JSON")
    next(button for button in page.button if button.label == "Inject document").click().run()
    assert not page.exception
    assert page.error[0].value.startswith("Invalid document:")


@pytest.mark.parametrize("action", ["confirm", "inject"])
def test_gate_issues_display_code_and_message_without_traceback(
    case_page, scanned_evidence, monkeypatch, action
):
    def fail(*args):
        raise GateError(
            [
                GateIssue(code="SYNTHETIC_gate", message="SYNTHETIC gate detail"),
                GateIssue(code="another_gate", message="Another detail"),
            ]
        )

    monkeypatch.setattr(
        app.Recoup, "confirm_field" if action == "confirm" else "add_evidence", fail
    )
    page, _ = case_page
    page.run()
    if action == "confirm":
        page.button(key=f"confirm:H:{scanned_evidence.evidence_id}:ocr_field").click().run()
    else:
        page.text_area(key="document-json:H").set_value(document().model_dump_json())
        next(button for button in page.button if button.label == "Inject document").click().run()
    assert not page.exception
    assert [error.value for error in page.error] == [
        "SYNTHETIC_gate: SYNTHETIC gate detail",
        "another_gate: Another detail",
    ]

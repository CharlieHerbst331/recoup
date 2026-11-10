"""Evidence presentation and document staging for design/02 §6."""

import shutil
import tempfile
from pathlib import Path, PurePosixPath

from recoup.app import Recoup
from recoup.contracts.bundle import BundleDoc
from recoup.contracts.models import CaseHistory, CaseView, Evidence, FieldTrust


def evidence_versions(case: CaseView, history: CaseHistory) -> list[Evidence]:
    versions = {row.evidence_id: row for row in case.evidence}
    for row in history.evidence_all:
        if not row.active:
            versions.setdefault(row.evidence_id, row)
    return list(versions.values())


def evidence_rows(versions: list[Evidence]) -> list[dict]:
    return [
        {
            "evidence_id": row.evidence_id,
            "doc_ref": row.doc_ref,
            "version": row.version,
            "kind": row.kind.value,
            "state": "active" if row.active else "superseded",
            "readable": row.readable,
            "method": row.method.value,
            "failure": row.failure.value if row.failure else "none",
        }
        for row in versions
    ]


def evidence_fields(evidence: Evidence, history: CaseHistory) -> list[dict[str, str]]:
    fields = evidence.fields.copy()
    trust = evidence.field_trust.copy()
    for fact in history.facts:
        if fact.evidence_id == evidence.evidence_id:
            fields[fact.key] = fact.value
            trust[fact.key] = fact.trust
    return [
        {
            "field": key,
            "value": str(fields.get(key)),
            "field_trust": trust.get(key, FieldTrust.source).value,
        }
        for key in sorted(fields.keys() | trust.keys())
    ]


def inject_document(
    service: Recoup,
    case_id: str,
    document_json: str,
    upload_name: str | None = None,
    upload_bytes: bytes | None = None,
) -> Evidence | None:
    doc = BundleDoc.model_validate_json(document_json)
    file = doc.file
    if upload_bytes is not None:
        file = file or upload_name
        if not file:
            raise ValueError("The uploaded file needs a filename.")
    elif file:
        raise ValueError("Upload the file named by BundleDoc.file, or omit file from the JSON.")
    if file:
        path = PurePosixPath(file.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in file or path == PurePosixPath("."):
            raise ValueError("BundleDoc.file must be a relative path inside the temporary folder.")
        if path.parts[0] == "document.json":
            raise ValueError("document.json is reserved for the BundleDoc JSON.")
        doc = doc.model_copy(update={"file": str(path)})

    folder = Path(tempfile.mkdtemp(prefix="recoup-evidence-"))
    # Retain scheduled uploads for release by World; see design/02 §4.4 and §6.
    scheduled = doc.available_at_day > service.world.clock.day()
    try:
        if doc.file and upload_bytes is not None:
            destination = folder / doc.file
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(upload_bytes)
        (folder / "document.json").write_text(doc.model_dump_json(), encoding="utf-8")
        return service.add_evidence(case_id, doc, str(folder))
    finally:
        if not scheduled:
            shutil.rmtree(folder)

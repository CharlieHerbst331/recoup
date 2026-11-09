"""Offline SQLite boundary checks for design/02 §§3.5, 4.2 and 5.7."""

import pytest

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.models import CaseStatus, Citation, FieldTrust, InsuranceStatus


def test_engine_status_strings_are_normalized(world, bundle):
    world.load_bundle(bundle)
    world.set_status("CASE", "needs_info", "claim_not_ready", "Missing evidence")
    view = world.view("CASE")
    assert view.status == CaseStatus.needs_info
    assert view.insurance == InsuranceStatus.claim_not_ready
    assert view.status_reason == "Missing evidence"


@pytest.mark.parametrize(
    ("status", "insurance"),
    [
        ("invalid", "watching"),
        ("proposed", "invalid"),
        ("", "watching"),
        ("proposed", ""),
    ],
)
def test_invalid_status_updates_leave_the_case_unchanged(world, bundle, status, insurance):
    world.load_bundle(bundle)
    world.set_status("CASE", CaseStatus.needs_info, InsuranceStatus.watching, "Original")
    before = tuple(world.db.execute("SELECT * FROM cases WHERE id='CASE'").fetchone())
    with pytest.raises(ValueError):
        world.set_status("CASE", status, insurance, "Changed")
    assert tuple(world.db.execute("SELECT * FROM cases WHERE id='CASE'").fetchone()) == before


def test_fact_change_events_reference_evidence_and_trace_the_revision(world, bundle):
    world.load_bundle(bundle)
    source = next(row for row in world.active_evidence("CASE") if row.doc_ref == "POD")
    revision = world.confirm_field(source.evidence_id, "signed", "Charles")
    history = world.history("CASE")
    event = history.events[-1]
    assert event.type == "evidence_added"
    assert world.evidence(event.ref) == source
    assert history.traces[-1].args["revision"] == {"kind": "fact", "id": revision.fact_id}
    count = len(history.events)
    assert world.confirm_field(source.evidence_id, "signed", "Charles") == revision
    assert len(world.history("CASE").events) == count


@pytest.mark.parametrize("cited", [False, True])
def test_explicit_line_reason_event_references_owning_evidence(world, bundle, cited):
    world.load_bundle(bundle)
    source = world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="REM",
            kind="remittance",
            title="SYNTHETIC remittance",
            fields={"ded.1.line_id": "D1", "ded.1.claimed_cents": 2000},
            text="Shortage",
        ),
    )
    citation = (
        Citation(evidence_id=source.evidence_id, locator="text", quote="Shortage")
        if cited
        else None
    )
    world.set_line_reason("CASE", "D1", "shortage", FieldTrust.model_extracted, citation)
    history = world.history("CASE")
    event = history.events[-1]
    assert event.type == "evidence_added"
    assert world.evidence(event.ref) == source
    assert history.traces[-1].args["revision"]["kind"] == "line_reason"
    assert history.traces[-1].args["revision"]["id"].startswith("R")
    count = len(history.events)
    world.set_line_reason("CASE", "D1", "shortage", FieldTrust.model_extracted, citation)
    assert len(world.history("CASE").events) == count


@pytest.mark.parametrize(("line_id", "source_ref"), [("U1", "PAY"), ("NP", "INV")])
def test_inferred_line_reason_event_references_ledger_evidence(world, bundle, line_id, source_ref):
    if line_id == "NP":
        bundle.docs = bundle.docs[:1]
    world.load_bundle(bundle)
    world.set_line_reason("CASE", line_id, "shortage", FieldTrust.human_confirmed, None)
    event = world.history("CASE").events[-1]
    assert event.type == "evidence_added"
    assert world.evidence(event.ref).doc_ref == source_ref


def test_line_revision_without_backing_evidence_keeps_trace_without_fake_event(world, bundle):
    world.load_bundle(bundle)
    # A persisted ledger can outlive missing source evidence in an older database.
    world.db.execute("DELETE FROM evidence WHERE case_id='CASE'")
    before = len(world.history("CASE").events)
    old_basis = world.evidence_set_hash("CASE")
    world.set_line_reason("CASE", "U1", "shortage", FieldTrust.human_confirmed, None)
    history = world.history("CASE")
    assert len(history.events) == before
    assert world.evidence_set_hash("CASE") != old_basis
    assert world.deduction_lines("CASE")[0].reason == "shortage"
    assert history.traces[-1].args["revision"]["kind"] == "line_reason"

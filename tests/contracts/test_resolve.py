from datetime import datetime, timezone

import pytest

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import (
    Citation,
    DocStatus,
    EffectiveFact,
    Evidence,
    FactRevision,
    FactSet,
)
from recoup.contracts.resolve import resolve_citation

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


@pytest.fixture
def source():
    row = Evidence(
        evidence_id="EV-H-pod-v1",
        case_id="H",
        doc_ref="pod",
        version=1,
        kind="pod",
        title="POD",
        available_from=NOW,
        content_sha256="a" * 64,
        readable=True,
        method="text",
        text="Received 360 cases.\n Signed true.\fLater 400 cases.",
        fields={"received.SKU-1": 360, "signed": True, "note": " two  words ", "empty": None},
        active=True,
    )
    basis = FactSet(
        case_id="H",
        basis_hash="basis-old",
        facts=[],
        docs=[
            DocStatus(
                evidence_id=row.evidence_id,
                doc_ref=row.doc_ref,
                kind=row.kind,
                readable=True,
                failure=None,
            )
        ],
    )
    return row, basis


@pytest.mark.parametrize(
    ("locator", "quote", "expected"),
    [
        ("fields.received.SKU-1", "360", 360),
        ("fields.signed", "true", True),
        ("fields.note", "two words", " two  words "),
        ("fields.empty", "None", None),
        ("text", "360  cases.\nSigned", "360 cases. Signed"),
        ("page:1", "Signed true.", "Signed true."),
        ("page:2", "Later 400", "Later 400"),
    ],
)
def test_source_locator_resolution(source, locator, quote, expected):
    row, basis = source
    citation = Citation(evidence_id=row.evidence_id, locator=locator, quote=quote)
    assert resolve_citation(citation, basis, [row], []) == expected


@pytest.mark.parametrize(
    ("locator", "quote"),
    [
        ("fields.received.SKU-1", "400"),
        ("fields.missing", "None"),
        ("fields.signed", "True"),
        ("text", "invented quote"),
        ("page:0", "Received"),
        ("page:3", "Later"),
        ("page:-1", "Later"),
        ("page:x", "Later"),
        ("page:1", "Later 400"),
        ("unknown", "360"),
        ("fact:F-missing", "360"),
    ],
)
def test_invalid_citation_rejected(source, locator, quote):
    row, basis = source
    with pytest.raises(GateError) as caught:
        resolve_citation(
            Citation(evidence_id=row.evidence_id, locator=locator, quote=quote), basis, [row], []
        )
    assert caught.value.issues[0].code == "invalid_citation"


def revision(row, fact_id, value):
    return FactRevision(
        fact_id=fact_id,
        case_id=row.case_id,
        evidence_id=row.evidence_id,
        key="received.SKU-1",
        value=value,
        trust="model_extracted",
        citation=Citation(evidence_id=row.evidence_id, locator="text", quote=f"{value} cases"),
        at=NOW,
        by="model",
    )


def with_fact(basis, row, fact):
    return basis.model_copy(
        update={
            "facts": [
                EffectiveFact(
                    evidence_id=row.evidence_id,
                    doc_kind=row.kind,
                    doc_ref=row.doc_ref,
                    key=fact.key,
                    value=fact.value,
                    trust=fact.trust,
                    origin="fact",
                    fact_id=fact.fact_id,
                    citation=Citation(
                        evidence_id=row.evidence_id,
                        locator=f"fact:{fact.fact_id}",
                        quote=str(fact.value),
                    ),
                )
            ]
        }
    )


def test_historical_fact_resolves_after_revision_without_world(source):
    row, basis = source
    before = row.model_dump_json()
    old, new = revision(row, "F-H-001", 360), revision(row, "F-H-002", 400)
    new.supersedes_fact_id = old.fact_id
    old_basis, new_basis = with_fact(basis, row, old), with_fact(basis, row, new)
    old_citation = old_basis.facts[0].citation
    assert resolve_citation(old_citation, old_basis, [row], [old, new]) == 360
    assert resolve_citation(new_basis.facts[0].citation, new_basis, [row], [old, new]) == 400
    with pytest.raises(GateError, match="superseded_citation"):
        resolve_citation(old_citation, new_basis, [row], [old, new])
    assert row.model_dump_json() == before


def test_historical_evidence_uses_basis_membership(source):
    row, basis = source
    row.active = False
    row.superseded_by = "EV-H-pod-v2"
    citation = Citation(evidence_id=row.evidence_id, locator="fields.signed", quote="true")
    assert resolve_citation(citation, basis, [row], []) is True
    with pytest.raises(GateError, match="superseded_citation"):
        resolve_citation(citation, basis.model_copy(update={"docs": []}), [row], [])


@pytest.mark.parametrize("defect", ["missing_source", "wrong_quote", "other_evidence", "cycle"])
def test_fact_provenance_is_validated(source, defect):
    row, basis = source
    fact = revision(row, "F-H-001", 360)
    fact_basis = with_fact(basis, row, fact)
    if defect == "missing_source":
        fact.citation = None
    elif defect == "wrong_quote":
        fact.citation.quote = "fabricated 360 cases"
    elif defect == "other_evidence":
        fact.citation.evidence_id = "EV-OTHER-pod-v1"
    else:
        fact.citation = fact_basis.facts[0].citation
    with pytest.raises(GateError, match="invalid_citation"):
        resolve_citation(fact_basis.facts[0].citation, fact_basis, [row], [fact])


def test_missing_and_cross_case_evidence_rejected(source):
    row, basis = source
    citation = Citation(evidence_id=row.evidence_id, locator="text", quote="360")
    for rows in [[], [row.model_copy(update={"case_id": "other"})]]:
        with pytest.raises(GateError, match="invalid_citation"):
            resolve_citation(citation, basis, rows, [])

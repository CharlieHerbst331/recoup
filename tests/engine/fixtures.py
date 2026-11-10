"""SYNTHETIC contract-model inputs for design/02 §3.2–3.7 and §5.3."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from recoup.contracts.models import (
    Citation,
    DeductionLine,
    DocStatus,
    EffectiveFact,
    Evidence,
    ExtractFailure,
    ExtractMethod,
    FactRevision,
    FactSet,
    FieldTrust,
    LedgerEntry,
)
from recoup.contracts.money import Money

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
VECTOR_DIR = Path(__file__).with_name("vectors")


def load_vectors(stage: str | None = None) -> list[dict]:
    result = []
    for path in sorted(VECTOR_DIR.glob("*.json")):
        document = json.loads(path.read_text())
        if stage is None or document["stage"] == stage:
            result.extend(document["vectors"])
    return result


def line_input(data: dict) -> DeductionLine:
    return DeductionLine(
        line_id=data["line_id"],
        reason=data["reason"],
        claimed=Money(cents=data["claimed_cents"]),
        sku=data.get("sku"),
        qty=data.get("qty"),
        buyer_ref=data.get("ref"),
    )


def evidence_input(data: dict, case_id: str) -> Evidence:
    fields = data["fields"].copy()
    readable = data.get("readable", True)
    trust = FieldTrust(data.get("trust", "source"))
    text = "SYNTHETIC document" if readable else ""
    content = json.dumps({"text": text, "fields": fields}, sort_keys=True)
    return Evidence(
        evidence_id=data["id"],
        case_id=case_id,
        doc_ref=data["id"],
        version=1,
        kind=data["kind"],
        title=f"SYNTHETIC {data['id']}",
        available_from=NOW,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        readable=readable,
        method=(
            ExtractMethod(trust.value)
            if trust in (FieldTrust.ocr, FieldTrust.vision)
            else ExtractMethod.structured
        ),
        failure=None if readable else ExtractFailure.empty_text,
        text=text,
        fields=fields,
        field_trust={key: trust for key in fields},
        active=True,
    )


def fact_inputs(
    documents: list[dict], case_id: str
) -> tuple[FactSet, list[Evidence], list[FactRevision]]:
    evidence, facts, revisions = [], [], []
    for data in documents:
        row = evidence_input(data, case_id)
        evidence.append(row)
        if not row.readable:
            continue
        for key, value in row.fields.items():
            quote = str(value).lower() if isinstance(value, bool) else str(value)
            source = Citation(evidence_id=row.evidence_id, locator=f"fields.{key}", quote=quote)
            trust = row.field_trust[key]
            fact_id = None
            citation = source
            if data.get("confirmed"):
                fact_id = f"F-{row.evidence_id}-{key}"
                trust = FieldTrust.human_confirmed
                revisions.append(
                    FactRevision(
                        fact_id=fact_id,
                        case_id=case_id,
                        evidence_id=row.evidence_id,
                        key=key,
                        value=value,
                        trust=trust,
                        citation=source,
                        at=NOW,
                        by="test-human",
                    )
                )
                citation = Citation(
                    evidence_id=row.evidence_id, locator=f"fact:{fact_id}", quote=quote
                )
            facts.append(
                EffectiveFact(
                    evidence_id=row.evidence_id,
                    doc_kind=row.kind,
                    doc_ref=row.doc_ref,
                    key=key,
                    value=value,
                    trust=trust,
                    origin="fact" if fact_id else "source",
                    fact_id=fact_id,
                    citation=citation,
                )
            )
    members = [f"E:{row.evidence_id}:{row.content_sha256}" for row in evidence]
    members.extend(f"F:{row.fact_id}" for row in revisions)
    basis_hash = hashlib.sha256("\n".join(sorted(members)).encode()).hexdigest()
    return (
        FactSet(
            case_id=case_id,
            basis_hash=basis_hash,
            facts=facts,
            docs=[
                DocStatus(
                    evidence_id=row.evidence_id,
                    doc_ref=row.doc_ref,
                    kind=row.kind,
                    readable=row.readable,
                    failure=row.failure,
                )
                for row in evidence
            ],
        ),
        evidence,
        revisions,
    )


def rule_inputs(vector: dict) -> tuple[list[DeductionLine], FactSet, list[LedgerEntry]]:
    case_id = vector["id"]
    data = vector["input"]
    line = line_input(data["line"])
    line.source_evidence_id = "vector-remittance"
    documents = list(data["documents"])
    # Authoring line metadata is supplied as a typed remittance source (§3.7).
    deduction = {
        "ded.1.line_id": line.line_id,
        "ded.1.reason": line.reason.value,
        "ded.1.claimed_cents": line.claimed.cents,
    }
    for key in ("sku", "qty", "ref", "reported_date"):
        if key in data["line"]:
            deduction[f"ded.1.{key}"] = data["line"][key]
    documents.append({"id": "vector-remittance", "kind": "remittance", "fields": deduction})
    facts, _, _ = fact_inputs(documents, case_id)
    ledger = [
        LedgerEntry(
            entry_id=f"L-{index}",
            case_id=case_id,
            kind=row["event"],
            amount=Money(cents=row["amount_cents"]),
            line_id=row.get("line_id"),
            source="SYNTHETIC prior credit",
            at=NOW,
        )
        for index, row in enumerate(data.get("ledger", []), 1)
    ]
    return [line], facts, ledger

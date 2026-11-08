"""Real app-built integration acceptance; BLOCKED without G1/G2 providers."""

from datetime import date
from hashlib import sha256
from importlib.util import find_spec

import pytest

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.models import Citation, LineAmount, Money
from recoup.contracts.testing import NullController
from recoup.engine.derive import derive, static_output
from recoup.engine.gates import ProposalValidator
from recoup.engine.tools import ToolSessionFactory

from .fixtures import load_vectors


@pytest.fixture
def real_world():
    if find_spec("recoup.app") is None:
        pytest.skip("BLOCKED G1/G2: recoup.app.build and real SqliteWorld are absent")
    from recoup.app import RecoupConfig, build

    return build(RecoupConfig(db=":memory:"), controller=NullController()).world


def bundle(*, received=400, cap=180000, policy=False):
    vectors = {v["id"]: v for v in load_vectors("run_rules")}
    docs = [
        BundleDoc(doc_ref=d["id"], kind=d["kind"], title="SYNTHETIC", fields=d["fields"])
        for d in vectors["hero_d1_before_pod_v2"]["input"]["documents"]
    ]
    for doc in docs:
        if doc.kind == "pod":
            doc.fields["received.SKU-1"] = received
        if doc.kind == "contract":
            doc.fields["promo.FALL26.cap_cents"] = cap
    docs.append(
        BundleDoc(
            doc_ref="remittance",
            kind="remittance",
            title="SYNTHETIC",
            fields={
                "ded.1.line_id": "D1",
                "ded.1.reason": "shortage",
                "ded.1.sku": "SKU-1",
                "ded.1.claimed_cents": 312000,
                "ded.2.line_id": "D2",
                "ded.2.reason": "promo_rebate",
                "ded.2.ref": "FALL26",
                "ded.2.claimed_cents": 312000,
            },
        )
    )
    if policy:
        docs.append(
            BundleDoc(
                doc_ref="policy",
                kind="insurance_policy",
                title="SYNTHETIC",
                fields={
                    "claim_doc.1": "pod",
                    "waiting_days_after_notice": 60,
                    "disputed_debt_clause": "notice_still_required",
                    "credit_limit_cents": 1000000,
                },
            )
        )
    return CaseBundle(
        case_id="SYNTHETIC-I",
        title="SYNTHETIC",
        seller="SYNTHETIC seller",
        buyer="SYNTHETIC buyer",
        currency="USD",
        invoice_ref="invoice",
        start_date=date(2026, 10, 20),
        allowed_recipients={
            target: ["SYNTHETIC recipient"]
            for target in ["mock_buyer_portal", "mock_erp", "mock_email", "mock_insurer"]
        },
        docs=docs,
    )


def start(world, **kwargs):
    b = bundle(**kwargs)
    assert world.load_bundle(b).status == "loaded"
    s = ToolSessionFactory().open(world, b.case_id, "integration", "test")
    decide(s)
    return s


def decide(s):
    result = s.call("run_rules", {})
    assert result.ok
    result = s.call(
        "propose_decision",
        {
            "lines": [
                dict(
                    line_id=f["line_id"],
                    verdict=f["verdict"],
                    citations=f["citations"],
                    rationale="SYNTHETIC",
                )
                for f in result.result["findings"]
            ]
        },
    )
    assert result.ok and result.result["accepted"]


def post(world, p):
    p = p.model_copy(
        update={
            "recipient": "SYNTHETIC recipient",
            "draft_text": "SYNTHETIC MOCK; LLM fake.",
            "draft_sha256": sha256(b"SYNTHETIC MOCK; LLM fake.").hexdigest(),
        }
    )
    assert ProposalValidator().validate(world, p, "save") == []
    p = world.save_proposal(p)
    assert ProposalValidator().validate(world, p, "approve") == []
    world.approve(p.proposal_id, p.version, "test-human")
    assert ProposalValidator().validate(world, p, "submit") == []
    return world.submit(p.proposal_id, p.version)


def test_real_propose_fact_and_fabrication(real_world):
    w = real_world
    s = start(w)
    doc = w.add_evidence(
        "SYNTHETIC-I",
        BundleDoc(
            doc_ref="text-pod", kind="pod", title="SYNTHETIC", text="SYNTHETIC received 360 cases"
        ),
    )
    args = dict(
        evidence_id=doc.evidence_id,
        key="received.SKU-1",
        value=360,
        citation=dict(evidence_id=doc.evidence_id, locator="text", quote="received 360 cases"),
    )
    assert s.call("propose_fact", args).result["accepted"]
    result = s.call("propose_fact", {**args, "value": 361})
    assert not result.ok and result.issues[0].code == "fabricated_fact"


def test_real_superseded_citation(real_world):
    w = real_world
    s = start(w)
    old = next(d for d in w.active_evidence("SYNTHETIC-I") if d.kind == "pod")
    w.add_evidence(
        "SYNTHETIC-I",
        BundleDoc(
            doc_ref=old.doc_ref,
            version=2,
            kind="pod",
            title="SYNTHETIC",
            fields={"signed": True, "received.SKU-1": 360},
        ),
    )
    result = s.call(
        "propose_fact",
        dict(
            evidence_id=old.evidence_id,
            key="signed",
            value=True,
            citation=Citation(
                evidence_id=old.evidence_id, locator="fields.signed", quote="true"
            ).model_dump(),
        ),
    )
    assert not result.ok and result.issues[0].code == "superseded_citation"


@pytest.mark.parametrize("kind,line", [("credit_memo", "D2"), ("dispute", "D1")])
def test_real_edited_allocations_rejected(real_world, kind, line):
    w = real_world
    start(w)
    p = next(p for p in derive(w, "SYNTHETIC-I", [line]) if p.kind == kind)
    p.recipient = "SYNTHETIC recipient"
    p.created_by = "human_edit"
    p.allocations[0] = LineAmount(line_id=line, amount=Money(cents=p.amount.cents + 1))
    p.amount = p.allocations[0].amount
    for stage in ("save", "approve", "submit"):
        assert "unsupported_allocation" in {
            i.code for i in ProposalValidator().validate(w, p, stage)
        }


@pytest.mark.parametrize(
    "text,blocked",
    [
        ("Coverage is guaranteed.", True),
        ("Does not establish coverage or eligibility.", False),
        ('Policy says "not covered".', False),
        ("cash collected: $0", False),
    ],
)
def test_real_assertion_gate(real_world, text, blocked):
    w = real_world
    start(w)
    p = next(p for p in derive(w, "SYNTHETIC-I") if p.kind == "dispute")
    p.recipient = "SYNTHETIC recipient"
    p.draft_text = text
    p.draft_sha256 = sha256(text.encode()).hexdigest()
    assert (
        "affirmative_assertion" in {i.code for i in ProposalValidator().validate(w, p, "save")}
    ) is blocked


def test_real_hero_credit_correction_no_repost(real_world):
    w = real_world
    s = start(w)
    initial = derive(w, "SYNTHETIC-I")
    for p in initial:
        post(w, p)
    old = next(d for d in w.active_evidence("SYNTHETIC-I") if d.kind == "pod")
    w.add_evidence(
        "SYNTHETIC-I",
        BundleDoc(
            doc_ref=old.doc_ref,
            version=2,
            kind="pod",
            title="SYNTHETIC",
            fields={"signed": True, "received.SKU-1": 360},
        ),
    )
    decide(s)
    new = derive(w, "SYNTHETIC-I")
    assert {p.kind.value: p.amount.cents for p in new} == {
        "credit_memo": 312000,
        "correction": 312000,
    }
    for p in new:
        post(w, p)
    assert w.ledger_balance("SYNTHETIC-I").cents == 132000
    assert derive(w, "SYNTHETIC-I") == []


def test_real_receipt_correction_allocation(real_world):
    w = real_world
    s = start(w, cap=302000)
    original = next(p for p in derive(w, "SYNTHETIC-I", ["D2"]) if p.kind == "dispute")
    r1 = post(w, original)

    def change(cap, version):
        old = next(d for d in w.active_evidence("SYNTHETIC-I") if d.kind == "contract")
        w.add_evidence(
            "SYNTHETIC-I",
            BundleDoc(
                doc_ref=old.doc_ref,
                version=version,
                kind="contract",
                title="SYNTHETIC",
                fields={"promo.FALL26.earned": True, "promo.FALL26.cap_cents": cap},
            ),
        )
        decide(s)

    change(300000, 2)
    supplement = next(p for p in derive(w, "SYNTHETIC-I", ["D2"]) if p.kind == "dispute")
    assert supplement.amount.cents == 2000 and supplement.business_key.endswith(":inc:1")
    r2 = post(w, supplement)
    change(309000, 3)
    corrections = [p for p in derive(w, "SYNTHETIC-I", ["D2"]) if p.kind == "correction"]
    assert [(p.corrects_receipt_id, p.amount.cents) for p in corrections] == [
        (r2.receipt_id, 2000),
        (r1.receipt_id, 7000),
    ]
    for p in corrections:
        post(w, p)
    change(311000, 4)
    p = next(p for p in derive(w, "SYNTHETIC-I", ["D2"]) if p.kind == "correction")
    assert p.amount.cents == 2000 and p.business_key.endswith(f":correction:{r1.receipt_id}:2")


def test_real_readiness_errors_and_isolation(real_world):
    w = real_world
    s = start(w)
    for args, code in [
        ({"kind": "dispute"}, "line_id_required"),
        ({"kind": "notice", "line_id": "D1"}, "line_id_not_allowed"),
        ({"kind": "dispute", "line_id": "unknown"}, "unknown_line"),
    ]:
        result = s.call("readiness", args)
        assert not result.ok and result.issues[0].code == code
    old = next(d for d in w.active_evidence("SYNTHETIC-I") if d.kind == "pod")
    w.add_evidence(
        "SYNTHETIC-I",
        BundleDoc(
            doc_ref=old.doc_ref,
            version=2,
            kind="pod",
            title="SYNTHETIC",
            text="SYNTHETIC incomplete POD",
        ),
    )
    decide(s)
    assert (
        s.call("readiness", {"kind": "dispute", "line_id": "D1"}).result["readiness"]["status"]
        == "not_ready"
    )
    assert (
        s.call("readiness", {"kind": "dispute", "line_id": "D2"}).result["readiness"]["status"]
        == "ready"
    )


def test_real_static_claim_items(real_world):
    w = real_world
    start(w, policy=True)
    items = {i.item_id: i.status for i in static_output(w, "SYNTHETIC-I").claim_items}
    assert items["claim.doc.pod"] == "present" and items["claim.notice_receipt"] == "missing"

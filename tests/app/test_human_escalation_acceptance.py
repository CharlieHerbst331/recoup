"""Human-routing acceptance through actual app assembly; design/02 §5.1 and §5.3."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import LLMResponse
from recoup.contracts.testing import ScriptedLLM

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "condition,reason",
    [
        ("legal_missing", "legal authority not supplied"),
        ("legal_unreadable", "legal authority unreadable"),
        ("negative_claim", "negative deduction: D2"),
    ],
)
def test_direct_decision_request_preserves_human_escalation(condition, reason):
    bundle = CaseBundle.model_validate_json(
        (ROOT / "cases/ambition/counteroffer/bundle.json").read_text()
    )
    remittance = next(doc for doc in bundle.docs if doc.kind == "remittance")
    if condition == "negative_claim":
        remittance.fields["ded.2.claimed_cents"] = -1
    else:
        remittance.fields["ded.2.requires_legal_review"] = True
        if condition == "legal_unreadable":
            bundle.docs.append(
                BundleDoc(
                    doc_ref="LEGAL-UNREADABLE",
                    kind="legal_authority",
                    title="SYNTHETIC unreadable legal authority",
                    file="missing-legal-authority.pdf",
                )
            )
    service = build(RecoupConfig(db=":memory:"))
    try:
        assert service.runtime_provider == "engine"
        service.world.load_bundle(bundle)
        before = service.world.ledger(bundle.case_id)
        # An LLM may request a decision before calling run_rules. The real scoped
        # adapter still invokes the actual assembled engine and SQLite World.
        service.controller.llm = ScriptedLLM(
            [
                LLMResponse(
                    model_id="SYNTHETIC-direct-decision",
                    mode="fake",
                    tool_calls=[
                        {
                            "id": "direct-decision",
                            "name": "propose_decision",
                            "arguments": {"lines": []},
                        }
                    ],
                )
            ]
        )
        view = service.run(bundle.case_id)[0]
        assert view.status == "needs_human"
        assert reason in view.status_reason
        assert service.world.current_decision(bundle.case_id) is None
        assert view.receipts == []
        assert service.world.ledger(bundle.case_id) == before
        assert service.controller._case_ids is None
    finally:
        service.world.close()

"""SYNTHETIC owned unit lane for 007-4; not real persistence proof."""

from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import LLMResponse
from recoup.contracts.testing import ScriptedLLM
from recoup.engine.config import HarnessConfig
from recoup.engine.factory import build_engine, get_llm, harness_controller
from recoup.engine.harness import SYSTEM, HarnessEngine
from recoup.engine.ingest import Ingestor
from recoup.engine.llm import FakeLLM, ReplayLLM
from recoup.engine.llm.replay import recording_key
from recoup.engine.tools import ToolSessionFactory

from .fixtures import fact_inputs
from .test_policy_readiness import inputs
from .tool_support import ToolWorld, hero


def scripted(*calls):
    return ScriptedLLM(
        [
            LLMResponse(
                model_id="scripted", mode="fake", tool_calls=[dict(id=str(i), name=n, arguments=a)]
            )
            for i, (n, a) in enumerate(calls)
        ]
    )


def run(world, llm=None, config=None, **kw):
    return HarnessEngine(config=config, **kw).investigate(
        world, world.facts.case_id, llm or FakeLLM(), "unit-run"
    )


def test_hero_day_zero_and_fake_trace():
    w = hero()
    w.state.decision = None
    result = run(w)
    assert result.status != "needs_human"
    assert [(p.kind, p.amount.cents) for p in result.proposals] == [
        ("dispute", 444000),
        ("credit_memo", 180000),
    ]
    assert [(d.valid.cents, d.disputed.cents) for d in result.decision.lines] == [
        (0, 312000),
        (180000, 132000),
    ]
    assert result.decision.llm_mode == "fake"
    assert result.decision.model_id == "offline-fakellm"
    assert all(
        "SYNTHETIC" in p.draft_text and "MOCK" in p.draft_text and "LLM fake" in p.draft_text
        for p in result.proposals
    )
    assert not result.receipts
    assert all(p.status == "proposed" for p in result.proposals)
    models = [t for t in w.traces if t.kind == "model_call"]
    assert models and all(
        t.llm_mode == "fake" and t.request and t.observation_sha256 for t in models
    )
    assert all(t.llm_mode == "fake" for t in w.traces if t.kind == "tool_call")
    assert "submit_approved" not in {s["name"] for s in models[0].request["tools"]}
    assert [t.tool for t in w.traces if t.kind == "tool_call"][-1] == "end"


def insured_mixed():
    w = hero()
    facts, evidence, revisions = inputs(pod="absent")
    # Keep the hero's invoice facts and add this synthetic policy only.
    policy = next(e for e in evidence if e.kind == "insurance_policy")
    fields = dict(policy.fields)
    fields.update(
        {
            "covered_buyer.1": "BUYER",
            "mep_days_after_due": 0,
        }
    )
    pf, pe, pr = fact_inputs(
        [
            dict(id="insured-policy", kind="insurance_policy", fields=fields),
            dict(
                id="insured-invoice",
                kind="invoice",
                fields={
                    "buyer_id": "BUYER",
                    "invoice_date": "2026-08-03",
                    "due_date": "2026-09-02",
                },
            ),
        ],
        w.facts.case_id,
    )
    # Only the shortage line loses its POD; pricing remains independently proven.
    pod_ids = {e.evidence_id for e in w.inventory if e.kind == "pod"}
    w.inventory = [e for e in w.inventory if e.evidence_id not in pod_ids] + pe
    w.facts.docs = [d for d in w.facts.docs if d.evidence_id not in pod_ids] + pf.docs
    w.facts.facts = [f for f in w.facts.facts if f.evidence_id not in pod_ids] + pf.facts
    w.revisions += pr
    w.state.evidence = w.inventory
    w.state.decision = None
    return w


def test_missing_pod_does_not_block_pricing_or_notice():
    w = insured_mixed()
    result = run(w)
    assert result.status != "needs_human", result.status_reason
    assert result.decision.lines[0].verdict == "needs_info"
    assert result.decision.lines[1].verdict == "partial"
    assert {(p.kind.value, tuple(a.line_id for a in p.allocations)) for p in result.proposals} >= {
        ("info_request", ("D1",)),
        ("dispute", ("D2",)),
        ("credit_memo", ("D2",)),
        ("insurer_notice", ()),
    }
    notice = next(r for r in result.readiness if r.kind == "notice")
    assert notice.status == "ready"
    assert next(i for i in notice.items if i.item_id == "notice.dispute_status").status == "unknown"


def test_end_refused_until_completion():
    w = hero()
    w.state.decision = None
    run(w, scripted(("end", {"reason": "premature"})))
    end = next(t for t in w.traces if t.tool == "end")
    assert end.result["result"] == {"accepted": False, "unmet": ["current decision"]}
    assert w.state.status == "needs_human"
    assert "current decision" in w.state.status_reason


def test_wrong_proven_verdict_is_overridden_and_original_traced():
    w = hero()
    run(
        w,
        scripted(
            (
                "propose_decision",
                {
                    "lines": [
                        dict(
                            line_id="D1",
                            verdict="valid",
                            citations=[],
                            rationale="SYNTHETIC scripted wrong verdict",
                        )
                    ]
                },
            )
        ),
    )
    assert w.state.decision.lines[0].verdict == "invalid"
    assert w.state.decision.lines[0].disputed.cents == 312000
    model = next(t for t in w.traces if t.kind == "model_call")
    assert model.result["tool_calls"][0]["arguments"]["lines"][0]["verdict"] == "valid"
    tool = next(t for t in w.traces if t.tool == "propose_decision")
    assert tool.args["lines"][0]["verdict"] == "invalid"


def test_loop_guard_and_keeps_prior_work():
    w = hero()
    result = run(
        w,
        scripted(
            (
                "draft_proposal",
                dict(
                    kind="credit_memo",
                    line_ids=["D2"],
                    recipient="SYNTHETIC recipient",
                    draft_text="SYNTHETIC MOCK LLM fake review",
                    citations=[],
                ),
            ),
            ("run_rules", {}),
            ("run_rules", {}),
        ),
    )
    assert result.status == "needs_human"
    assert "loop" in result.status_reason
    assert len(result.proposals) == 1
    assert w.traces[-1].result["reason"] == "loop"


@pytest.mark.parametrize(
    "name,args", [("unknown_tool", {}), ("read_evidence", {}), ("end", {"reason": "not done"})]
)
def test_tool_error_budget(name, args):
    w = hero()
    result = run(w, scripted((name, args)), HarnessConfig(max_tool_errors=1))
    assert result.status == "needs_human"
    assert "tool errors" in result.status_reason


def test_step_wall_and_empty_response_limits():
    w = hero()
    result = run(w, config=HarnessConfig(max_steps=1))
    assert "steps" in result.status_reason
    ticks = iter([0, 121])
    w = hero()
    assert "wall time" in run(w, timer=lambda: next(ticks)).status_reason
    llm = ScriptedLLM([LLMResponse(tool_calls=[], model_id="empty", mode="fake")])
    assert "tool errors" in run(hero(), llm, HarnessConfig(max_tool_errors=1)).status_reason


def test_budget_config_cannot_exceed_treatment():
    for settings in [
        dict(max_steps=17),
        dict(max_tool_errors=5),
        dict(max_wall_s=121),
        dict(max_steps=0),
        dict(max_wall_s=0),
    ]:
        with pytest.raises(ValueError):
            HarnessConfig(**settings)


def test_factory_selection_and_controller_delegation():
    parts = build_engine(SimpleNamespace(llm="fake"))
    assert isinstance(parts.engine, HarnessEngine)
    assert isinstance(parts.ingestor, Ingestor)
    assert isinstance(parts.tools, ToolSessionFactory)
    assert parts.engine.tools is parts.tools
    assert isinstance(get_llm(SimpleNamespace(llm="fake")), FakeLLM)
    assert isinstance(get_llm(SimpleNamespace(llm="replay", model="recorded")), ReplayLLM)
    with pytest.raises(ValueError):
        get_llm(SimpleNamespace(llm="invalid"))
    calls = []
    engine = SimpleNamespace(
        handle=lambda *a: calls.append(("handle", a)),
        investigate=lambda *a: calls.append(("investigate", a)),
    )
    llm = FakeLLM()
    controller = harness_controller(SimpleNamespace(engine=engine), llm)
    w = SimpleNamespace(list_cases=lambda: [SimpleNamespace(case_id="case")])
    controller.react(w, [], "run")
    assert calls == [("handle", (w, llm, "run")), ("investigate", (w, "case", llm, "run"))]
    idle = SimpleNamespace(
        pending_events=lambda: [],
        due=lambda until: [],
        clock=SimpleNamespace(now=lambda: None),
    )
    assert parts.engine.handle(idle, llm, "run") == []


def test_rules_only_has_no_model_calls():
    w = hero()
    out = HarnessEngine().rules_only(w, w.facts.case_id)
    assert len(out.lines) == 2 and len(out.proposals) == 2
    assert all(t.kind != "model_call" for t in w.traces)


def test_replay_exact_key_and_no_fallback(tmp_path):
    replay = ReplayLLM("recorded-model", tmp_path)
    response = LLMResponse(
        model_id="recorded-model",
        mode="live",
        input_tokens=17,
        output_tokens=5,
        tool_calls=[dict(id="1", name="end", arguments={})],
    )
    request = (SYSTEM, [{"role": "user", "content": "SYNTHETIC"}], [{"name": "end"}])
    replay.record(*request, response)
    replay.record(*request, response)
    result = replay.next(*request)
    assert result.mode == "replay" and result.input_tokens == 17
    assert result.tool_calls == response.tool_calls
    assert len(list(tmp_path.glob("*.json"))) == 1
    with pytest.raises(FileNotFoundError):
        replay.next("changed", request[1], request[2])
    with pytest.raises(ValueError, match="Conflicting"):
        replay.record(*request, response.model_copy(update={"text": "different"}))
    with pytest.raises(ValueError):
        replay.record(*request, result)
    assert recording_key("v1", "m", "s", [], [{"a": 1, "b": 2}]) == recording_key(
        "v1", "m", "s", [], [{"b": 2, "a": 1}]
    )
    assert recording_key("v1", "m", "s", [], []) != recording_key("v2", "m", "s", [], [])


def doc(**kw):
    return BundleDoc(doc_ref="SYNTHETIC", kind="pod", title="SYNTHETIC input", **kw)


def write_pdf(path, *, text=True, encrypted=False):
    writer = PdfWriter()
    for word in ("SYNTHETIC POD signed", "received 360"):
        page = writer.add_blank_page(width=300, height=300)
        if text:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    )
                }
            )
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 10 100 Td ({word}) Tj ET".encode())
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("secret")
    writer.write(path)


def test_generated_text_pdf_is_usable_by_fact_tool(tmp_path):
    path = tmp_path / "magic.txt"
    write_pdf(path)
    output = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert output.readable and output.method == "text_pdf"
    assert output.text == "SYNTHETIC POD signed\freceived 360"
    facts, evidence, revisions = fact_inputs(
        [dict(id="pdf", kind="pod", fields={})], "SYNTHETIC-PDF"
    )
    evidence[0].text = output.text
    evidence[0].method = output.method
    w = ToolWorld(facts, evidence, revisions, [], [])
    result = (
        ToolSessionFactory()
        .open(w, facts.case_id, "pdf", "harness")
        .call(
            "propose_fact",
            dict(
                evidence_id=evidence[0].evidence_id,
                key="received.A",
                value=360,
                citation=dict(
                    evidence_id=evidence[0].evidence_id, locator="page:2", quote="received 360"
                ),
            ),
        )
    )
    assert result.ok and result.result["accepted"]


@pytest.mark.parametrize(
    "name,data,failure",
    [
        ("broken.pdf", b"%PDF-1.7\nbroken", "corrupt"),
        ("broken.pdf", b"broken", "corrupt"),
        ("image.txt", b"\x89PNG\r\n\x1a\nSYNTHETIC", "ocr_unavailable"),
        ("bad.txt", b"\xff", "corrupt"),
        ("unknown.bin", b"arbitrary", "unsupported"),
        ("empty.txt", b"", "empty_text"),
    ],
)
def test_ingest_failure_statuses(tmp_path, name, data, failure, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: False)
    (tmp_path / name).write_bytes(data)
    result = Ingestor().ingest(doc(file=name, fields={"signed": True}), str(tmp_path))
    if failure == "empty_text":
        # Structured facts remain usable when an actual text file is empty.
        assert result.readable
        result = Ingestor().ingest(doc(file=name), str(tmp_path))
    assert not result.readable and result.method == "none" and result.failure == failure
    assert not result.text and not result.fields


@pytest.mark.parametrize("encrypted,failure", [(True, "encrypted"), (False, "ocr_unavailable")])
def test_encrypted_and_scanned_pdf(tmp_path, encrypted, failure, monkeypatch):
    monkeypatch.setattr("recoup.engine.ingest.ocr_available", lambda: False)
    path = tmp_path / "input.pdf"
    write_pdf(path, text=False, encrypted=encrypted)
    result = Ingestor().ingest(doc(file=path.name), str(tmp_path))
    assert result.failure == failure and not result.readable


def test_structured_text_eml_and_missing_file(tmp_path):
    ingestor = Ingestor()
    result = ingestor.ingest(doc(fields={"signed": True}))
    assert result.readable and result.method == "structured"
    assert result.field_trust == {"signed": "source"}
    assert ingestor.ingest(doc(text="SYNTHETIC inline")).method == "text"
    for name in ("input.txt", "input.eml"):
        (tmp_path / name).write_text("SYNTHETIC text", encoding="utf-8")
        assert ingestor.ingest(doc(file=name), str(tmp_path)).text == "SYNTHETIC text"
    assert ingestor.ingest(doc(file="missing.txt"), str(tmp_path)).failure == "corrupt"
    assert ingestor.ingest(doc(file="missing.txt")).failure == "corrupt"
    assert ingestor.ingest(doc(file="../outside.txt"), str(tmp_path)).failure == "unsupported"


def test_overcredit_is_escalated_without_discarding_state():
    w = hero()
    from recoup.contracts.models import LedgerEntry, Money

    from .fixtures import NOW

    w.entries.append(
        LedgerEntry(
            entry_id="overcredit",
            case_id=w.facts.case_id,
            kind="credit_posted",
            amount=Money(cents=180001),
            line_id="D2",
            source="SYNTHETIC",
            at=NOW,
        )
    )
    result = run(w)
    assert result.status == "needs_human"
    assert "over_credited" in result.status_reason
    assert result.decision is not None


def test_no_insurer_recipient_still_computes_notice_readiness():
    w = insured_mixed()
    original = w.allowed_recipients
    from recoup.contracts.models import Target

    w.allowed_recipients = lambda case_id, target: (
        [] if target == Target.mock_insurer else original(case_id, target)
    )
    result = run(w)
    assert any(r.kind == "notice" for r in result.readiness)
    assert any(p.kind == "dispute" for p in result.proposals)


def test_tool_session_injection_uses_only_protocol_methods():
    w = hero()
    delegate = ToolSessionFactory().open(w, w.facts.case_id, "injected", "harness")
    calls = []

    class Session:
        def schemas(self):
            return delegate.schemas()

        def call(self, name, args):
            calls.append(name)
            return delegate.call(name, args)

    class Factory:
        def open(self, world, case_id, run_id, controller):
            assert world is w and case_id == w.facts.case_id
            return Session()

    result = run(w, tools=Factory())
    assert result.status != "needs_human"
    assert calls[-1] == "end"

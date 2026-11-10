"""007-5 real-provider acceptance; no double is persistence proof."""

from datetime import timedelta
from importlib.util import find_spec

import pytest

from recoup.contracts.bundle import BundleDoc, BundleEvent
from recoup.contracts.models import DueWork
from recoup.contracts.testing import NullController
from recoup.engine.harness import HarnessEngine
from recoup.engine.llm import FakeLLM

from .test_007_3_integration import bundle, post
from .test_007_4_integration import load


@pytest.fixture
def world():
    if find_spec("recoup.app") is None:
        pytest.skip("BLOCKED G2/G3: app.build and real SqliteWorld transactions/events absent")
    from recoup.app import RecoupConfig, build

    return build(RecoupConfig(db=":memory:"), controller=NullController()).world


def handle(world):
    return HarnessEngine().handle(world, FakeLLM(), "real-scheduler")


def initial(world):
    cid = load(world)
    handle(world)
    return cid


def test_real_day_three_correction_credit_no_repost(world):
    b = bundle()
    pod = next(d for d in b.docs if d.kind == "pod")
    b.events.append(
        BundleEvent(
            at_day=3,
            type="add_doc",
            doc=BundleDoc(
                doc_ref=pod.doc_ref,
                version=2,
                kind="pod",
                title="SYNTHETIC",
                fields={"signed": True, "received.SKU-1": 360},
            ),
        )
    )
    world.load_bundle(b)
    handle(world)
    for p in world.view(b.case_id).proposals:
        post(world, p)
    handle(world)
    world.advance_to(3)
    handle(world)
    current = [p for p in world.view(b.case_id).proposals if p.status == "proposed"]
    assert sorted((p.kind.value, p.amount.cents) for p in current) == [
        ("correction", 312000),
        ("credit_memo", 312000),
    ]
    assert len(world.view(b.case_id).receipts) == 2
    assert handle(world) == []


@pytest.mark.parametrize("reply", [False, True])
def test_real_silence_and_reply(world, reply):
    cid = initial(world)
    post(world, next(p for p in world.view(cid).proposals if p.kind == "dispute"))
    handle(world)
    if reply:
        world.advance_to(5)
        world.add_evidence(
            cid,
            BundleDoc(
                doc_ref="reply",
                kind="email",
                title="SYNTHETIC",
                fields={"from": "SYNTHETIC recipient"},
            ),
        )
        handle(world)
        assert not [
            d for d in world.view(cid).due if d.kind == "follow_up" and d.status == "pending"
        ]
    world.advance_to(15)
    handle(world)
    assert len([p for p in world.view(cid).proposals if p.kind == "follow_up"]) == (
        0 if reply else 1
    )
    before = world.view(cid)
    assert handle(world) == []
    assert world.view(cid) == before


def test_real_notice_and_claim_dates(world):
    cid = load(world, mixed=True)
    handle(world)
    notice = next(r for r in world.readiness(cid) if r.kind == "notice")
    due = next(d for d in world.view(cid).due if d.kind == "notice_deadline")
    assert due.due_at.date() == notice.deadline - timedelta(days=7)
    world.advance_to(world.clock.day() + (due.due_at.date() - world.clock.now().date()).days)
    handle(world)
    assert world.view(cid).insurance == "notice_due"
    post(world, next(p for p in world.view(cid).proposals if p.kind == "insurer_notice"))
    handle(world)
    due = next(d for d in world.view(cid).due if d.kind == "claim_window")
    world.advance_to(world.clock.day() + (due.due_at.date() - world.clock.now().date()).days)
    handle(world)
    assert any(p.kind == "claim_package" for p in world.view(cid).proposals)


def test_real_mid_event_exception_rolls_back(world, monkeypatch):
    cid = load(world)
    before = world.view(cid)
    pending = world.pending_events()
    original = world.save_proposal

    def crash(proposal):
        original(proposal)
        raise RuntimeError("SYNTHETIC crash after save")

    with monkeypatch.context() as patch:
        patch.setattr(world, "save_proposal", crash)
        with pytest.raises(RuntimeError, match="crash after save"):
            handle(world)
    assert world.view(cid) == before
    assert world.pending_events() == pending
    handle(world)
    assert len(world.view(cid).proposals) == 2
    assert handle(world) == []


@pytest.mark.parametrize(
    "sender,is_buyer",
    [
        ("SYNTHETIC email-only", True),
        ("SYNTHETIC portal-only", True),
        ("SYNTHETIC erp-only", False),
    ],
)
@pytest.mark.parametrize("process_reply_event", [True, False])
def test_real_reply_allowlists(world, monkeypatch, sender, is_buyer, process_reply_event):
    b = bundle()
    b.allowed_recipients["mock_email"] = ["SYNTHETIC email-only"]
    b.allowed_recipients["mock_buyer_portal"] += ["SYNTHETIC portal-only"]
    b.allowed_recipients["mock_erp"] += ["SYNTHETIC erp-only"]
    world.load_bundle(b)
    handle(world)
    post(world, next(p for p in world.view(b.case_id).proposals if p.kind == "dispute"))
    handle(world)
    followup_due = next(d for d in world.view(b.case_id).due if d.kind == "follow_up")
    acknowledgements = []
    mark_due = world.mark_due

    def record_due(due_id, status):
        mark_due(due_id, status)
        acknowledgements.append((due_id, status))

    monkeypatch.setattr(world, "mark_due", record_due)
    world.advance_to(14)
    world.add_evidence(
        b.case_id,
        BundleDoc(
            doc_ref="distinct-sender-reply",
            kind="email",
            title="SYNTHETIC",
            fields={"from": sender},
        ),
    )
    if not process_reply_event:
        # Refresh the decision after the evidence cascade, without handling the email event.
        HarnessEngine().investigate(world, b.case_id, FakeLLM(), "refresh-reply")
        for event in world.pending_events():
            world.mark_event(event.event_id)
    handle(world)
    view = world.view(b.case_id)
    followups = [p for p in view.proposals if p.kind == "follow_up"]
    assert len(followups) == (0 if is_buyer else 1)
    expected_status = "cancelled" if is_buyer and process_reply_event else "done"
    assert (followup_due.due_id, expected_status) in acknowledgements
    assert not [d for d in view.due if d.kind == "follow_up"]
    assert handle(world) == []


def test_real_event_due_ordering(world, monkeypatch):
    cid = load(world)
    start = world.clock.now()
    for due_id, at in [
        ("SYNTHETIC-z", start),
        ("SYNTHETIC-a", start),
        ("SYNTHETIC-earlier", start - timedelta(hours=1)),
        ("SYNTHETIC-later", start + timedelta(days=1)),
        ("SYNTHETIC-future", start + timedelta(days=2)),
    ]:
        world.schedule(
            DueWork(
                due_id=due_id,
                case_id=cid,
                kind="recheck",
                due_at=at,
                basis=world.evidence_set_hash(cid),
                idempotency_key=due_id,
            )
        )
    world.advance_to(1)
    for i in range(2):
        world.add_evidence(
            cid,
            BundleDoc(
                doc_ref=f"ordering-note-{i}",
                kind="collection_note",
                title="SYNTHETIC",
                text=f"SYNTHETIC collection note {i}",
            ),
        )
    events = sorted(world.pending_events(), key=lambda e: (e.at, e.seq))
    expected = [
        ("due", "SYNTHETIC-earlier"),
        *[("event", e.event_id) for e in events if e.at == start],
        ("due", "SYNTHETIC-a"),
        ("due", "SYNTHETIC-z"),
        *[("event", e.event_id) for e in events if e.at > start],
        ("due", "SYNTHETIC-later"),
    ]
    observed = []
    mark_event, mark_due = world.mark_event, world.mark_due
    pending_events, due = world.pending_events, world.due

    def record_event(event_id):
        mark_event(event_id)
        observed.append(("event", event_id))

    def record_due(due_id, status):
        mark_due(due_id, status)
        observed.append(("due", due_id))

    monkeypatch.setattr(world, "mark_event", record_event)
    monkeypatch.setattr(world, "mark_due", record_due)
    monkeypatch.setattr(world, "pending_events", lambda: list(reversed(pending_events())))
    monkeypatch.setattr(world, "due", lambda until: list(reversed(due(until))))
    engine = HarnessEngine()
    monkeypatch.setattr(engine, "investigate", lambda w, c, llm, run: w.view(c))
    assert engine.handle(world, FakeLLM(), "real-ordering") == [cid]
    assert observed == expected
    assert (
        next(d for d in world.view(cid).due if d.due_id == "SYNTHETIC-future").status == "pending"
    )
    assert engine.handle(world, FakeLLM(), "real-ordering-retry") == []
    assert observed == expected

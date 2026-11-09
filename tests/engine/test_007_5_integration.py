"""007-5 real-provider acceptance; no double is persistence proof."""

from datetime import timedelta
from importlib.util import find_spec

import pytest

from recoup.contracts.bundle import BundleDoc, BundleEvent
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

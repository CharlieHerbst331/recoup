"""Independent regression-gate comparisons; real engine acceptance remains G3."""

from datetime import date, datetime, timedelta, timezone

import pytest

import recoup.app as app_module
from recoup.app import Recoup, RecoupConfig
from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.models import (
    CaseHistory,
    Citation,
    DocStatus,
    EffectiveFact,
    Evidence,
    FactSet,
    LoadResult,
    ProposalKind,
    Verdict,
)
from recoup.contracts.oracle import (
    CaseOracle,
    LineOracle,
    StaticClaimItemOut,
    StaticLineOut,
    StaticOutput,
    StaticProposalOut,
)
from recoup.contracts.resolve import resolve_citation
from recoup.contracts.testing import NullController, ScriptedLLM, stub_parts

START = date(2026, 10, 20)


def sample_bundle(case_id="SYNTHETIC-R"):
    return CaseBundle(
        case_id=case_id,
        title="SYNTHETIC regression comparator fixture",
        seller="Synthetic seller",
        buyer="Synthetic buyer",
        currency="USD",
        invoice_ref="INV-UNIT",
        start_date=START,
        static_day=9,
        docs=[
            BundleDoc(
                doc_ref="INV",
                kind="invoice",
                title="SYNTHETIC invoice",
                fields={"total_cents": 1000},
                text="SYNTHETIC invoice total 1000 cents.",
            ),
            BundleDoc(
                doc_ref="TERMS",
                kind="contract",
                title="SYNTHETIC price terms",
                fields={"price.SKU-1_cents": 80},
                text="SYNTHETIC price is 80 cents.",
            ),
            BundleDoc(
                doc_ref="POD",
                kind="pod",
                title="SYNTHETIC unsigned POD",
                fields={"signed": False},
                text="SYNTHETIC unsigned receipt.",
            ),
        ],
    )


def sample_oracle(case_id="SYNTHETIC-R"):
    return CaseOracle(
        case_id=case_id,
        expected_status="loaded",
        lines=[
            LineOracle(
                line_id="D1",
                verdict="partial",
                valid_cents=200,
                disputed_cents=100,
                required_refs=["INV#fields.total_cents", "TERMS#fields.price.SKU-1_cents"],
                acceptable_refs=["INV#fields.total_cents", "TERMS#fields.price.SKU-1_cents"],
            ),
            LineOracle(
                line_id="D2",
                verdict="needs_info",
                valid_cents=None,
                disputed_cents=None,
                required_refs=["POD"],
                acceptable_refs=["POD"],
                missing=["signed_pod"],
            ),
        ],
        proposals=[
            StaticProposalOut(kind="credit_memo", line_ids=["D1"], amount_cents=200),
            StaticProposalOut(kind="dispute", line_ids=["D1"], amount_cents=100),
            StaticProposalOut(kind="info_request", line_ids=["D2"], amount_cents=None),
        ],
        forbidden_kinds=["correction"],
        notice_deadline=date(2027, 1, 13),
        claim_items={"claim.credit_limit": "restricted"},
        oracle_sentinel="ORACLE-ONLY-SYNTHETIC-REGRESSION-UNIT",
    )


def evidence_id(case_id, ref):
    return f"E-{case_id}-{ref}"


def sample_output(case_id="SYNTHETIC-R"):
    return StaticOutput(
        case_id=case_id,
        lines=[
            StaticLineOut(
                line_id="D1",
                verdict="partial",
                valid_cents=200,
                disputed_cents=100,
                citations=[
                    Citation(
                        evidence_id=evidence_id(case_id, "INV"),
                        locator="fields.total_cents",
                        quote="1000",
                    ),
                    Citation(
                        evidence_id=evidence_id(case_id, "TERMS"),
                        locator="fields.price.SKU-1_cents",
                        quote="80",
                    ),
                ],
            ),
            StaticLineOut(
                line_id="D2",
                verdict="needs_info",
                valid_cents=None,
                disputed_cents=None,
                citations=[
                    Citation(
                        evidence_id=evidence_id(case_id, "POD"),
                        locator="fields.signed",
                        quote="false",
                    )
                ],
            ),
        ],
        proposals=sample_oracle(case_id).proposals,
        missing={"D2": ["signed_pod"]},
        notice_deadline=date(2027, 1, 13),
        claim_items=[StaticClaimItemOut(item_id="claim.credit_limit", status="restricted")],
    )


class RegressionClock:
    def __init__(self):
        self.current_day = 0

    def day(self):
        return self.current_day

    def now(self):
        return datetime.combine(
            START + timedelta(days=self.current_day), datetime.min.time(), timezone.utc
        )


class RegressionWorld:
    """Only regression orchestration and pure quote resolution; no SQL or engine."""

    def __init__(self, calls, load_mutator=None):
        self.calls = calls
        self.clock = RegressionClock()
        self.load_mutator = load_mutator
        self.loaded = None
        self.evidence_rows = []
        self.basis = None

    def __getattr__(self, name):
        raise NotImplementedError(f"Unexpected RegressionWorld operation: {name}")

    def load_bundle(self, bundle, bundle_dir=None):
        assert isinstance(bundle, CaseBundle)
        self.calls.append(("load", bundle.case_id, bundle_dir))
        self.loaded = bundle
        if bundle.currency == "USD":
            self.evidence_rows = [
                Evidence(
                    evidence_id=evidence_id(bundle.case_id, doc.doc_ref),
                    case_id=bundle.case_id,
                    doc_ref=doc.doc_ref,
                    version=doc.version,
                    kind=doc.kind,
                    title=doc.title,
                    available_from=self.clock.now(),
                    content_sha256=f"unit-{doc.doc_ref}",
                    readable=True,
                    method="structured",
                    text=doc.text,
                    fields=doc.fields,
                    active=True,
                )
                for doc in bundle.docs
            ]
            self.basis = FactSet(
                case_id=bundle.case_id,
                basis_hash="unit-basis",
                docs=[
                    DocStatus(
                        evidence_id=e.evidence_id,
                        doc_ref=e.doc_ref,
                        kind=e.kind,
                        readable=True,
                        failure=None,
                    )
                    for e in self.evidence_rows
                ],
                facts=[
                    EffectiveFact(
                        evidence_id=e.evidence_id,
                        doc_kind=e.kind,
                        doc_ref=e.doc_ref,
                        key=key,
                        value=value,
                        trust="source",
                        origin="source",
                        fact_id=None,
                        citation=Citation(
                            evidence_id=e.evidence_id,
                            locator=f"fields.{key}",
                            quote=str(value).lower() if isinstance(value, bool) else str(value),
                        ),
                    )
                    for e in self.evidence_rows
                    for key, value in e.fields.items()
                ],
            )
        result = LoadResult(
            case_id=bundle.case_id, status="loaded" if bundle.currency == "USD" else "quarantined"
        )
        return self.load_mutator(result) if self.load_mutator else result

    def advance_to(self, day, release_events=True):
        self.calls.append(("advance", day, release_events))
        assert release_events is False, "Regression evaluation must freeze event inventory"
        assert self.loaded is not None
        assert day == self.loaded.static_day
        self.clock.current_day = day
        return []

    def history(self, case_id):
        assert case_id == self.loaded.case_id
        self.calls.append(("history", case_id))
        return CaseHistory(
            case_id=case_id,
            evidence_all=self.evidence_rows,
            facts=[],
            reasons=[],
            decisions=[],
            proposals_all=[],
            approvals=[],
            receipts=[],
            attempts=[],
            ledger=[],
            events=[],
            traces=[],
        )

    def resolve_citation(self, citation, basis_hash=None):
        self.calls.append(("resolve", citation.evidence_id, citation.locator))
        return resolve_citation(citation, self.basis, self.evidence_rows, [])

    def close(self):
        self.calls.append(("close",))


class RegressionService:
    def __init__(self, output, load_mutator=None):
        self.calls = []
        self.world = RegressionWorld(self.calls, load_mutator)
        self.output = output

    def __getattr__(self, name):
        raise NotImplementedError(f"Unexpected RegressionService operation: {name}")

    def run(self, case_id=None):
        assert self.world.clock.day() == self.world.loaded.static_day
        self.calls.append(("run", case_id))
        return []

    def static_output(self, case_id):
        self.calls.append(("static_output", case_id))
        return self.output

    def history(self, case_id):
        return self.world.history(case_id)


def write_case(directory, bundle=None, oracle=None):
    bundle = bundle or sample_bundle()
    oracle = oracle or sample_oracle(bundle.case_id)
    directory.mkdir(parents=True)
    (directory / "bundle.json").write_text(bundle.model_dump_json())
    (directory / "oracle.json").write_text(oracle.model_dump_json())
    return bundle, oracle


@pytest.fixture
def gate(monkeypatch):
    configs, services = [], []
    source_config = RecoupConfig(db="do-not-open.db", model="configured-model", run_id="unit-run")
    outer = Recoup(source_config, object(), NullController(), stub_parts(), ScriptedLLM([]))

    def install(outputs=None, load_mutator=None):
        queue = list(outputs or [sample_output()])

        def fake_build(config=None, **kwargs):
            assert isinstance(config, RecoupConfig)
            assert config is not outer.config
            assert config.db == ":memory:"
            assert config.model == source_config.model and config.llm == "fake"
            assert "controller" not in kwargs
            configs.append(config.model_copy(deep=True))
            service = RegressionService(queue.pop(0), load_mutator)
            services.append(service)
            return service

        monkeypatch.setattr(app_module, "build", fake_build)
        return outer, configs, services

    return install


def assert_failure(results):
    assert results
    assert any(passed is False and issues for _, passed, issues in results), results


def test_matching_oracle_passes_with_frozen_clock_and_validated_refs(tmp_path, gate):
    write_case(tmp_path / "r01")
    outer, configs, services = gate()
    assert outer.check_regression(str(tmp_path)) == [("SYNTHETIC-R", True, [])]
    assert outer.config.db == "do-not-open.db"
    assert len(configs) == len(services) == 1
    calls = services[0].calls
    assert calls[:4] == [
        ("load", "SYNTHETIC-R", str(tmp_path / "r01")),
        ("advance", 9, False),
        ("run", "SYNTHETIC-R"),
        ("static_output", "SYNTHETIC-R"),
    ]
    assert calls[-1] == ("close",)
    assert {call[1:] for call in calls if call[0] == "resolve"} == {
        ("E-SYNTHETIC-R-INV", "fields.total_cents"),
        ("E-SYNTHETIC-R-TERMS", "fields.price.SKU-1_cents"),
        ("E-SYNTHETIC-R-POD", "fields.signed"),
    }


def test_each_sorted_case_gets_fresh_in_memory_build(tmp_path, gate):
    write_case(tmp_path / "r02", sample_bundle("SECOND"), sample_oracle("SECOND"))
    write_case(tmp_path / "r01", sample_bundle("FIRST"), sample_oracle("FIRST"))
    outer, configs, services = gate([sample_output("FIRST"), sample_output("SECOND")])
    assert outer.check_regression(str(tmp_path)) == [("FIRST", True, []), ("SECOND", True, [])]
    assert len(configs) == len(services) == 2
    assert services[0].world is not services[1].world


@pytest.mark.parametrize(
    "change",
    [
        "case_id",
        "missing_line",
        "extra_line",
        "duplicate_line",
        "verdict",
        "valid_cents",
        "disputed_cents",
        "missing_key",
        "missing_label",
        "missing_proposal",
        "duplicate_proposal",
        "proposal_kind",
        "proposal_lines",
        "proposal_amount",
        "nullable_amount",
        "deadline",
        "missing_claim_item",
        "claim_status",
        "duplicate_claim_item",
        "invalid_quote",
        "unknown_evidence",
        "missing_required_ref",
        "disallowed_ref",
    ],
)
def test_isolated_output_mismatches_fail(tmp_path, gate, change):
    write_case(tmp_path / "r01")
    output = sample_output()
    if change == "case_id":
        output.case_id = "OTHER"
    elif change == "missing_line":
        output.lines.pop()
    elif change == "extra_line":
        output.lines.append(output.lines[0].model_copy(update={"line_id": "EXTRA"}))
    elif change == "duplicate_line":
        output.lines.append(output.lines[0].model_copy(deep=True))
    elif change == "verdict":
        output.lines[0].verdict = Verdict.invalid
    elif change == "valid_cents":
        output.lines[0].valid_cents = 199
    elif change == "disputed_cents":
        output.lines[0].disputed_cents = 101
    elif change == "missing_key":
        output.missing = {}
    elif change == "missing_label":
        output.missing["D2"] = ["other"]
    elif change == "missing_proposal":
        output.proposals.pop()
    elif change == "duplicate_proposal":
        output.proposals.append(output.proposals[0].model_copy(deep=True))
    elif change == "proposal_kind":
        output.proposals[0].kind = ProposalKind.counteroffer
    elif change == "proposal_lines":
        output.proposals[0].line_ids = ["D2"]
    elif change == "proposal_amount":
        output.proposals[0].amount_cents = 201
    elif change == "nullable_amount":
        output.proposals[2].amount_cents = 0
    elif change == "deadline":
        output.notice_deadline = None
    elif change == "missing_claim_item":
        output.claim_items = []
    elif change == "claim_status":
        output.claim_items[0].status = "present"
    elif change == "duplicate_claim_item":
        output.claim_items.append(output.claim_items[0].model_copy(deep=True))
    elif change == "invalid_quote":
        output.lines[0].citations[0].quote = "999"
    elif change == "unknown_evidence":
        output.lines[0].citations[0].evidence_id = "E-OTHER-INV"
    elif change == "missing_required_ref":
        output.lines[0].citations.pop()
    elif change == "disallowed_ref":
        output.lines[0].citations.append(
            Citation(
                evidence_id=evidence_id("SYNTHETIC-R", "POD"),
                locator="fields.signed",
                quote="false",
            )
        )
    outer, _, _ = gate([StaticOutput.model_validate(output.model_dump())])
    assert_failure(outer.check_regression(str(tmp_path)))


def test_forbidden_proposal_fails_even_if_otherwise_expected(tmp_path, gate):
    oracle = sample_oracle()
    oracle.forbidden_kinds.append(ProposalKind.dispute)
    write_case(tmp_path / "r01", oracle=oracle)
    outer, _, _ = gate()
    assert_failure(outer.check_regression(str(tmp_path)))


@pytest.mark.parametrize("change", ["load_case", "load_status", "oracle_case"])
def test_load_and_oracle_identity_mismatches_fail(tmp_path, gate, change):
    oracle = sample_oracle()
    if change == "oracle_case":
        oracle.case_id = "OTHER"
    write_case(tmp_path / "r01", oracle=oracle)
    mutator = None
    if change == "load_case":

        def mutator(result):
            return result.model_copy(update={"case_id": "OTHER"})
    elif change == "load_status":

        def mutator(result):
            return result.model_copy(update={"status": "quarantined"})

    outer, _, _ = gate(load_mutator=mutator)
    assert_failure(outer.check_regression(str(tmp_path)))


def test_quarantine_passes_without_running_or_exporting_engine(tmp_path, gate):
    bundle = sample_bundle().model_copy(update={"currency": "EUR"})
    oracle = sample_oracle().model_copy(
        update={
            "expected_status": "quarantined",
            "lines": [],
            "proposals": [],
            "notice_deadline": None,
            "claim_items": {},
        }
    )
    write_case(tmp_path / "r01", bundle, oracle)
    outer, _, services = gate()
    assert outer.check_regression(str(tmp_path)) == [(bundle.case_id, True, [])]
    assert all(
        call[0] not in {"advance", "run", "static_output", "history", "resolve"}
        for call in services[0].calls
    )


def test_oracle_refs_accept_doc_refs_and_precise_locators(tmp_path, gate):
    oracle = sample_oracle()
    oracle.lines[0].required_refs = ["INV", "TERMS#fields.price.SKU-1_cents"]
    oracle.lines[0].acceptable_refs = ["INV", "TERMS#fields.price.SKU-1_cents"]
    write_case(tmp_path / "r01", oracle=oracle)
    outer, _, _ = gate()
    assert outer.check_regression(str(tmp_path)) == [(oracle.case_id, True, [])]


def test_line_and_proposal_order_does_not_create_false_mismatch(tmp_path, gate):
    write_case(tmp_path / "r01")
    output = sample_output()
    output.lines.reverse()
    output.proposals.reverse()
    outer, _, _ = gate([output])
    assert outer.check_regression(str(tmp_path)) == [(output.case_id, True, [])]


@pytest.mark.parametrize(
    "problem",
    [
        "missing_root",
        "empty_root",
        "missing_bundle",
        "missing_oracle",
        "invalid_bundle",
        "invalid_oracle",
    ],
)
def test_missing_or_invalid_fixture_inputs_fail_explicitly(tmp_path, gate, problem):
    directory = tmp_path / "cases"
    if problem not in {"missing_root", "empty_root"}:
        write_case(directory / "r01")
        if problem.startswith("missing_"):
            (
                directory
                / "r01"
                / ("bundle.json" if problem == "missing_bundle" else "oracle.json")
            ).unlink()
        else:
            (
                directory
                / "r01"
                / ("bundle.json" if problem == "invalid_bundle" else "oracle.json")
            ).write_text("{")
    elif problem == "empty_root":
        directory.mkdir()
    outer, _, _ = gate()
    try:
        results = outer.check_regression(str(directory))
    except (FileNotFoundError, NotADirectoryError):
        return
    assert_failure(results)


def test_proposal_line_order_is_normalized_without_dropping_duplicates(tmp_path, gate):
    oracle, output = sample_oracle(), sample_output()
    oracle.proposals[2].line_ids = ["D1", "D2"]
    output.proposals[2].line_ids = ["D2", "D1"]
    write_case(tmp_path / "r01", oracle=oracle)
    outer, _, _ = gate([output])
    assert outer.check_regression(str(tmp_path)) == [(output.case_id, True, [])]


@pytest.mark.parametrize(
    "line_index,field",
    [(0, "valid_cents"), (0, "disputed_cents"), (1, "valid_cents"), (1, "disputed_cents")],
)
def test_nullable_line_amounts_are_compared_exactly(tmp_path, gate, line_index, field):
    write_case(tmp_path / "r01")
    output = sample_output()
    setattr(output.lines[line_index], field, None if line_index == 0 else 0)
    outer, _, _ = gate([output])
    assert_failure(outer.check_regression(str(tmp_path)))


def test_duplicate_oracle_line_ids_fail(tmp_path, gate):
    oracle = sample_oracle()
    oracle.lines.append(oracle.lines[0].model_copy(deep=True))
    write_case(tmp_path / "r01", oracle=oracle)
    outer, _, _ = gate()
    assert_failure(outer.check_regression(str(tmp_path)))


def test_failed_case_does_not_hide_later_case(tmp_path, gate):
    write_case(tmp_path / "r01", sample_bundle("FIRST"), sample_oracle("FIRST"))
    write_case(tmp_path / "r02", sample_bundle("SECOND"), sample_oracle("SECOND"))
    bad = sample_output("FIRST")
    bad.lines[0].valid_cents = 201
    outer, _, services = gate([bad, sample_output("SECOND")])
    results = outer.check_regression(str(tmp_path))
    assert results[0][0] == "FIRST" and results[0][1] is False and results[0][2]
    assert results[1] == ("SECOND", True, [])
    assert all(service.calls[-1] == ("close",) for service in services)


@pytest.mark.parametrize(
    "extra",
    [
        "missing_key",
        "missing_label",
        "non_needs_info_missing",
        "claim_item",
        "duplicate_extra_claim_item",
        "info_request",
        "follow_up",
        "duplicate_info_request",
    ],
)
def test_permitted_nonfinancial_extras_do_not_fail_gate(tmp_path, gate, extra):
    """Scoring follows design/02 §8.6 subset requirements."""
    write_case(tmp_path / "r01")
    output = sample_output()
    if extra == "missing_key":
        output.missing["EXTRA"] = ["additional context"]
    elif extra == "missing_label":
        output.missing["D2"].append("additional context")
    elif extra == "non_needs_info_missing":
        output.missing["D1"] = ["additional context"]
    elif extra == "claim_item":
        output.claim_items.append(StaticClaimItemOut(item_id="claim.extra", status="missing"))
    elif extra == "duplicate_extra_claim_item":
        output.claim_items.extend(
            [
                StaticClaimItemOut(item_id="claim.extra", status="present"),
                StaticClaimItemOut(item_id="claim.extra", status="missing"),
            ]
        )
    elif extra == "duplicate_info_request":
        output.proposals.append(output.proposals[2].model_copy(deep=True))
    else:
        output.proposals.append(StaticProposalOut(kind=extra, line_ids=["D2"], amount_cents=None))
    outer, _, _ = gate([output])
    assert outer.check_regression(str(tmp_path)) == [(output.case_id, True, [])]


@pytest.mark.parametrize(
    "kind,amount",
    [
        ("dispute", None),
        ("credit_memo", None),
        ("correction", None),
        ("counteroffer", None),
        ("info_request", 0),
        ("follow_up", 1),
    ],
)
def test_extra_money_moving_proposals_fail_even_without_forbidden_kind(
    tmp_path, gate, kind, amount
):
    oracle, output = sample_oracle(), sample_output()
    oracle.forbidden_kinds = []
    write_case(tmp_path / "r01", oracle=oracle)
    output.proposals.append(StaticProposalOut(kind=kind, line_ids=["D2"], amount_cents=amount))
    outer, _, _ = gate([output])
    assert_failure(outer.check_regression(str(tmp_path)))


def test_extra_nonfinancial_proposal_still_fails_when_forbidden(tmp_path, gate):
    oracle, output = sample_oracle(), sample_output()
    oracle.forbidden_kinds.append(ProposalKind.follow_up)
    write_case(tmp_path / "r01", oracle=oracle)
    output.proposals.append(StaticProposalOut(kind="follow_up", line_ids=["D2"], amount_cents=None))
    outer, _, _ = gate([output])
    assert_failure(outer.check_regression(str(tmp_path)))


def test_oracle_proposal_multiplicity_requires_distinct_matches(tmp_path, gate):
    oracle = sample_oracle()
    oracle.proposals.append(oracle.proposals[2].model_copy(deep=True))
    write_case(tmp_path / "r01", oracle=oracle)
    outer, _, _ = gate()
    assert_failure(outer.check_regression(str(tmp_path)))

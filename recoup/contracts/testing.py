"""Small offline stubs for design/02 §3.5; no World implementation."""

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from .bundle import BundleDoc
from .interfaces import (
    EngineParts,
    GateError,
    IngestOutput,
    LLMClient,
    LLMResponse,
    ToolSession,
    World,
)
from .models import (
    Basis,
    CaseView,
    Citation,
    Decision,
    DomainEvent,
    ExtractFailure,
    ExtractMethod,
    GateIssue,
    LineDecision,
    Proposal,
    TraceEvent,
    Verdict,
)
from .oracle import StaticLineOut, StaticOutput
from .resolve import resolve_citation
from .tools import (
    TOOL_REGISTRY,
    EvidenceIndexRow,
    ListEvidenceArgs,
    ListEvidenceResult,
    ReadEvidenceArgs,
    ReadEvidenceResult,
    ToolEnvelope,
    tool_json_schemas,
)


class StubEngine:
    def investigate(self, world: World, case_id: str, llm: LLMClient, run_id: str) -> CaseView:
        current = world.current_decision(case_id)
        version = current.version + 1 if current else 1
        world.save_decision(
            Decision(
                decision_id=f"D-{case_id}-{version}",
                case_id=case_id,
                version=version,
                evidence_set_hash=world.evidence_set_hash(case_id),
                lines=[
                    LineDecision(
                        line_id=line.line_id,
                        verdict=Verdict.needs_info,
                        basis=Basis.missing_evidence,
                        valid=None,
                        disputed=None,
                        citations=[],
                        rationale="Contract stub: engine not implemented",
                    )
                    for line in world.deduction_lines(case_id)
                ],
                current=True,
                model_id="contract-stub",
                llm_mode="fake",
                prompt_version="stub",
                created_at=world.clock.now(),
            )
        )
        return world.view(case_id)

    def handle(self, world: World, llm: LLMClient, run_id: str) -> list[str]:
        return []

    def static_output(self, world: World, case_id: str) -> StaticOutput:
        return StaticOutput(
            case_id=case_id,
            lines=[
                StaticLineOut(
                    line_id=line.line_id,
                    verdict=Verdict.needs_info,
                    valid_cents=None,
                    disputed_cents=None,
                    citations=[],
                )
                for line in world.deduction_lines(case_id)
            ],
            proposals=[],
            missing={
                line.line_id: ["engine_not_implemented"] for line in world.deduction_lines(case_id)
            },
            notice_deadline=None,
        )

    def rules_only(self, world: World, case_id: str) -> StaticOutput:
        return self.static_output(world, case_id)


class PassValidator:
    def validate(
        self, world: World, proposal: Proposal, stage: Literal["save", "approve", "submit"]
    ) -> list[GateIssue]:
        return []


class TextOnlyIngestor:
    def ingest(self, doc: BundleDoc, bundle_dir: str | None) -> IngestOutput:
        text = doc.text
        if doc.file:
            failure = ExtractFailure.unsupported
            if bundle_dir is not None and Path(doc.file).suffix.lower() == ".txt":
                try:
                    text = (Path(bundle_dir) / doc.file).read_text(encoding="utf-8")
                    failure = None
                except (OSError, UnicodeError):
                    failure = ExtractFailure.corrupt
            if failure is not None:
                return IngestOutput(
                    text="",
                    fields={},
                    field_trust={},
                    readable=False,
                    method=ExtractMethod.none,
                    failure=failure,
                )
        readable = bool(text or doc.fields)
        return IngestOutput(
            text=text,
            fields=doc.fields.copy(),
            field_trust={},
            readable=readable,
            method=ExtractMethod.structured if doc.fields else ExtractMethod.text,
            failure=None if readable else ExtractFailure.empty_text,
        )


class _StubToolSession:
    def __init__(self, world: World, case_id: str, run_id: str, controller: str) -> None:
        self.world, self.case_id = world, case_id
        self.run_id, self.controller = run_id, controller
        self.step = 0

    def schemas(self) -> list[dict]:
        return [
            schema
            for schema in tool_json_schemas()
            if schema["name"] in {"list_evidence", "read_evidence"}
        ]

    def call(self, name: str, args: dict) -> ToolEnvelope:
        try:
            if name not in {"list_evidence", "read_evidence"}:
                envelope = ToolEnvelope(
                    ok=False,
                    result=None,
                    issues=[
                        GateIssue(
                            code="unsupported_tool", message=f"Contract stub has no tool {name}"
                        )
                    ],
                )
            else:
                parsed = TOOL_REGISTRY[name][0].model_validate(args)
                result = self._read(parsed)
                envelope = ToolEnvelope(ok=True, result=result)
        except GateError as exc:
            envelope = ToolEnvelope(ok=False, result=None, issues=exc.issues)
        except ValidationError as exc:
            envelope = ToolEnvelope(
                ok=False, result=None, issues=[GateIssue(code="invalid_args", message=str(exc))]
            )
        self.step += 1
        self.world.trace(
            TraceEvent(
                run_id=self.run_id,
                case_id=self.case_id,
                step=self.step,
                sim_time=self.world.clock.now(),
                kind="tool_call",
                tool=name,
                args=args,
                controller=self.controller,
                result=envelope.model_dump(mode="json"),
            )
        )
        return envelope

    def _read(self, args: ListEvidenceArgs | ReadEvidenceArgs) -> dict:
        rows = self.world.active_evidence(self.case_id)
        if isinstance(args, ListEvidenceArgs):
            if args.include_superseded:
                rows = self.world.history(self.case_id).evidence_all
            return ListEvidenceResult(
                rows=[
                    EvidenceIndexRow(
                        evidence_id=row.evidence_id,
                        doc_ref=row.doc_ref,
                        version=row.version,
                        kind=row.kind,
                        title=row.title,
                        readable=row.readable,
                        method=row.method.value,
                        failure=row.failure.value if row.failure else None,
                        active=row.active,
                        field_keys=sorted(row.fields),
                        text_chars=len(row.text),
                    )
                    for row in rows
                    if args.kind is None or row.kind == args.kind
                ]
            ).model_dump(mode="json")
        row = next((row for row in rows if row.evidence_id == args.evidence_id), None)
        if row is None:
            # Keep the stub case-bound even when World.evidence can read other cases.
            raise GateError([GateIssue(code="unknown_evidence", message=args.evidence_id)])
        text = row.text
        if args.locator:
            basis = self.world.fact_set(self.case_id)
            if args.locator.startswith("fields."):
                value = row.fields.get(args.locator.removeprefix("fields."))
                text = str(value).lower() if isinstance(value, bool) else str(value)
            elif args.locator.startswith("page:"):
                page = args.locator.removeprefix("page:")
                pages = row.text.split("\f")
                text = (
                    pages[int(page) - 1]
                    if page.isdecimal() and 1 <= int(page) <= len(pages)
                    else ""
                )
            elif args.locator.startswith("fact:"):
                fact_id = args.locator.removeprefix("fact:")
                fact = next(
                    (
                        fact
                        for fact in basis.facts
                        if fact.evidence_id == row.evidence_id and fact.fact_id == fact_id
                    ),
                    None,
                )
                if fact is None:
                    raise GateError([GateIssue(code="superseded_citation", message=args.locator)])
                text = fact.citation.quote
            resolve_citation(
                Citation(evidence_id=row.evidence_id, locator=args.locator, quote=text),
                basis,
                rows,
                self.world.history(self.case_id).facts,
            )
        limit = max(0, args.max_chars)
        return ReadEvidenceResult(
            evidence_id=row.evidence_id,
            active=row.active,
            text=text[:limit],
            truncated=len(text) > limit,
            source_fields=row.fields,
            facts=[
                fact
                for fact in self.world.fact_set(self.case_id).facts
                if fact.evidence_id == row.evidence_id
            ],
        ).model_dump(mode="json")


class StubToolSessionFactory:
    def open(self, world: World, case_id: str, run_id: str, controller: str) -> ToolSession:
        return _StubToolSession(world, case_id, run_id, controller)


class NullController:
    name = "null"

    def react(self, world: World, events: list[DomainEvent], run_id: str) -> None:
        pass


class ScriptedLLM:
    def __init__(self, responses: Iterable[LLMResponse]) -> None:
        self._responses = iter(responses)

    def next(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        return next(self._responses)


def stub_parts() -> EngineParts:
    return EngineParts(
        engine=StubEngine(),
        ingestor=TextOnlyIngestor(),
        validator=PassValidator(),
        tools=StubToolSessionFactory(),
    )

"""Bounded tool orchestration; design/02 §5.1–5.2, §5.6."""

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from time import monotonic

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import Target, TraceEvent
from recoup.engine import policy
from recoup.engine.config import PROMPT_VERSION, HarnessConfig
from recoup.engine.derive import derive, static_output
from recoup.engine.rules import NeedsHumanError, run_rules
from recoup.engine.tools import ToolSessionFactory

SYSTEM = (Path(__file__).parent / "prompts" / "system_v1.md").read_text(encoding="utf-8")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _draft_args(world, proposal, mode):
    recipients = world.allowed_recipients(proposal.case_id, proposal.target)
    return dict(
        kind=proposal.kind.value,
        line_ids=[a.line_id for a in proposal.allocations],
        recipient=recipients[0] if recipients else "",
        draft_text=f"SYNTHETIC data. MOCK action. LLM {mode}. Conditional offer for review."
        if proposal.kind == "counteroffer"
        else f"SYNTHETIC data. MOCK action. LLM {mode}. Please review the cited evidence.",
        citations=[c.model_dump(mode="json") for c in proposal.citations],
        corrects_receipt_id=proposal.corrects_receipt_id,
        offer_ref=proposal.offer_ref,
    )


class HarnessEngine:
    def __init__(self, tools=None, config=None, *, timer=monotonic):
        self.tools = tools or ToolSessionFactory()
        self.config = config or HarnessConfig()
        self.timer = timer

    def _observation(self, world, case_id, mode):
        view = world.view(case_id)
        decision = world.current_decision(case_id)
        current = bool(
            decision
            and decision.current
            and decision.evidence_set_hash == world.evidence_set_hash(case_id)
        )
        candidates = derive(world, case_id) if current else []
        existing = {
            p.business_key
            for p in view.proposals
            if p.evidence_set_hash == world.evidence_set_hash(case_id)
            and p.status in {"proposed", "approved", "submitted_mock"}
        }
        windows = policy.answer(
            world.fact_set(case_id),
            "claim_window",
            max(
                (r for r in view.receipts if ":insurer_notice:" in r.business_key),
                key=lambda r: (r.at, r.receipt_id),
                default=None,
            ),
        )
        summary = view.model_dump(mode="json")
        summary["evidence"] = [
            dict(evidence_id=e.evidence_id, kind=e.kind.value, title=e.title, readable=e.readable)
            for e in view.evidence
        ]
        return dict(
            unmet=self._unmet(world, case_id),
            claim_open=any(
                a.computed_date and a.computed_date <= world.clock.now().date() for a in windows
            ),
            case=summary,
            has_policy=any(d.kind == "insurance_policy" for d in world.fact_set(case_id).docs),
            current_decision=current,
            drafts=[
                _draft_args(world, p, mode) for p in candidates if p.business_key not in existing
            ],
            insurance_recipients=world.allowed_recipients(case_id, Target.mock_insurer)
            if any(d.kind == "insurance_policy" for d in world.fact_set(case_id).docs)
            else [],
        )

    def investigate(self, world, case_id, llm, run_id):
        session = self.tools.open(world, case_id, run_id, "harness")
        messages = []
        seen = set()
        errors = 0
        started = self.timer()
        reason = "steps"
        for step in range(1, self.config.max_steps + 1):
            if self.timer() - started >= self.config.max_wall_s:
                reason = "wall time"
                break
            mode = getattr(llm, "mode", "fake")
            try:
                observation = self._observation(world, case_id, mode)
            except (GateError, NeedsHumanError) as exc:
                return self._stop(world, case_id, run_id, step, session, str(exc))
            messages.append({"role": "user", "content": _json(observation)})
            request = dict(system=SYSTEM, messages=deepcopy(messages), tools=session.schemas())
            try:
                response = llm.next(**request)
            except (StopIteration, FileNotFoundError) as exc:
                reason = f"LLM unavailable: {type(exc).__name__}"
                break
            # Metadata is session-local; sharing a factory must not leak between runs.
            if hasattr(session, "factory"):
                session.factory = ToolSessionFactory(
                    model_id=response.model_id,
                    llm_mode=response.mode,
                    prompt_version=PROMPT_VERSION,
                )
            world.trace(
                TraceEvent(
                    run_id=run_id,
                    case_id=case_id,
                    step=step,
                    sim_time=world.clock.now(),
                    kind="model_call",
                    controller="harness",
                    model_id=response.model_id,
                    llm_mode=response.mode,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_ms=response.latency_ms,
                    model_text=response.text,
                    request=request,
                    result=response.model_dump(mode="json"),
                    observation_sha256=sha256(_json(request).encode()).hexdigest(),
                )
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": deepcopy(response.tool_calls),
                }
            )
            if not response.tool_calls:
                errors += 1
                if errors >= self.config.max_tool_errors:
                    return self._stop(world, case_id, run_id, step, session, "tool errors")
            for call in response.tool_calls:
                if self.timer() - started >= self.config.max_wall_s:
                    return self._stop(world, case_id, run_id, step, session, "wall time")
                if (
                    not isinstance(call, dict)
                    or not isinstance(call.get("name"), str)
                    or not isinstance(call.get("arguments"), dict)
                ):
                    errors += 1
                    messages.append({"role": "user", "content": "Malformed tool call"})
                else:
                    args = deepcopy(call["arguments"])
                    if call["name"] == "propose_decision" and isinstance(args.get("lines"), list):
                        findings = {
                            f.line_id: f
                            for f in run_rules(
                                world.view(case_id).lines,
                                world.fact_set(case_id),
                                world.ledger(case_id),
                            )
                        }
                        for line in args["lines"]:
                            if (
                                isinstance(line, dict)
                                and isinstance(line.get("line_id"), str)
                                and (f := findings.get(line["line_id"]))
                            ):
                                if f.basis == "proven":
                                    line["verdict"] = f.verdict.value
                    envelope = session.call(call["name"], args)
                    if any(i.code == "needs_human" for i in envelope.issues):
                        return world.view(case_id)
                    result = envelope.model_dump(mode="json")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", ""),
                            "name": call["name"],
                            "content": _json(result),
                        }
                    )
                    signature = _json([call["name"], args, result])
                    if signature in seen:
                        return self._stop(world, case_id, run_id, step, session, "loop")
                    seen.add(signature)
                    rejected = not envelope.ok or (envelope.result or {}).get("accepted") is False
                    errors += int(rejected)
                    if call["name"] == "end" and envelope.ok and envelope.result["accepted"]:
                        return world.view(case_id)
                if errors >= self.config.max_tool_errors:
                    return self._stop(world, case_id, run_id, step, session, "tool errors")
        return self._stop(world, case_id, run_id, self.config.max_steps, session, reason)

    def _unmet(self, world, case_id):
        try:
            return ToolSessionFactory().open(world, case_id, "completion", "harness").unmet()
        except (GateError, NeedsHumanError) as exc:
            return [str(exc)]

    def _stop(self, world, case_id, run_id, step, session, reason):
        unmet = self._unmet(world, case_id)
        detail = f"{reason}; unmet: {', '.join(unmet) or 'none'}"
        world.set_status(case_id, status="needs_human", reason=detail)
        world.trace(
            TraceEvent(
                run_id=run_id,
                case_id=case_id,
                step=step,
                sim_time=world.clock.now(),
                kind="budget",
                model_id=getattr(getattr(session, "factory", None), "model_id", ""),
                llm_mode=getattr(getattr(session, "factory", None), "llm_mode", ""),
                controller="harness",
                result_summary=detail,
                result={"reason": reason, "unmet": unmet},
            )
        )
        return world.view(case_id)

    def static_output(self, world, case_id):
        return static_output(world, case_id)

    def rules_only(self, world, case_id):
        session = self.tools.open(world, case_id, "rules-only", "rules_only")
        findings = run_rules(
            world.view(case_id).lines, world.fact_set(case_id), world.ledger(case_id)
        )
        session.call(
            "propose_decision",
            {
                "lines": [
                    dict(line_id=f.line_id, verdict=f.verdict.value, citations=[], rationale=f.note)
                    for f in findings
                ]
            },
        )
        for proposal in derive(world, case_id):
            session.call("draft_proposal", _draft_args(world, proposal, "fake"))
        return self.static_output(world, case_id)

    def handle(self, world, llm, run_id):
        from recoup.engine.scheduler import handle

        return handle(self, world, llm, run_id)

"""Case-bound tools using shared schemas; design/02 §3.4–3.8, §5.4–5.6."""

import re
from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

from pydantic import ValidationError

from recoup.contracts import tools as schema
from recoup.contracts.interfaces import GateError, TransientError, World
from recoup.contracts.models import (
    KIND_TARGET,
    Decision,
    DueWork,
    GateIssue,
    LineDecision,
    Proposal,
    TraceEvent,
)
from recoup.contracts.money import Money, fmt
from recoup.engine import policy, readiness
from recoup.engine.derive import allocations, derive, receipt_kind
from recoup.engine.gates import ProposalValidator
from recoup.engine.rules import NeedsHumanError, run_rules

_KEYS = {
    "invoice": (
        r"invoice_no|invoice_date|due_date|buyer_id|total_cents"
        r"|line\.[1-9]\d*\.(sku|qty|unit_price_cents)"
    ),
    "payment": r"invoice_no|paid_cents|paid_date|payment_ref",
    "remittance": (
        r"invoice_no|paid_cents|ded\.[1-9]\d*\.(line_id|reason"
        r"|claimed_cents|sku|qty|ref|reported_date)"
    ),
    "debit_memo": (
        r"invoice_no|ded\.[1-9]\d*\.(line_id|reason|claimed_cents|sku|qty"
        r"|ref|reported_date)"
    ),
    "po": r"po_no|required_delivery_date|line\.[1-9]\d*\.(sku|qty|unit_price_cents)",
    "contract": (
        r"contract_id|effective_date|price\.[^.]+_cents|early_pay_bp"
        r"|early_pay_days|late_penalty_bp|late_grace_days"
        r"|damage_window_days|damage_late_waived|promo\.[^.]+\.(cap_cents"
        r"|earned)|returns_require_rma|required_delivery_date"
    ),
    "bol": r"bol_no|ship_date|shipped\.[^.]+",
    "pod": r"pod_no|delivered_date|signed|received\.[^.]+|refused\.[^.]+|exception_note",
    "tracking": r"delivered_date|carrier",
    "inspection": r"report_date|sku|damaged_qty|cause",
    "return_auth": r"rma_no|sku|authorized_qty|received_qty|received_date",
    "credit_memo": r"credit_no|invoice_no|amount_cents|line_id",
    "statement": r"as_of|balance_cents",
    "collection_note": r"date|channel",
    "company_policy": (
        r"tolerance_cents|follow_up_days|authority_cents"
        r"|allowed_authority_roles|amendment_precedence"
    ),
    "insurance_policy": (
        r"policy_id|covered_buyer\.[1-9]\d*|credit_limit_cents|period_start"
        r"|period_end|mep_days_after_due|notice_days_after_mep"
        r"|waiting_days_after_notice|claim_doc\.[1-9]\d*"
        r"|disputed_debt_clause|stop_shipment_after_mep|clause\.[a-z_]+"
        r"|exclusion\.[1-9]\d*"
    ),
}
_KEYS["amendment"] = _KEYS["contract"] + r"|amends|authorized_by|authority_role"
_KEYS["email"] = _KEYS["amendment"] + r"|from|to|sent_date"


def _fail(code, message, line_id=None):
    raise GateError([GateIssue(code=code, message=message, line_id=line_id)])


def _render(value):
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def _contains(value, quote, key):
    rendered = [_render(value)]
    if key.endswith("_cents") and type(value) is int:
        dollars = fmt(Money(cents=value))
        rendered += [
            dollars,
            dollars.replace(",", ""),
            dollars.replace("$", ""),
            dollars.replace(",", "").replace("$", ""),
        ]
    normalized = " ".join(quote.split()).replace("$", "")
    rendered = [v.replace("$", "") for v in rendered]
    return any(
        re.search(r"(?<![\w.+-])" + re.escape(v) + r"(?![\w.])", normalized) for v in rendered if v
    )


class ToolSessionFactory:
    def __init__(self, *, model_id="fake", llm_mode="fake", prompt_version="v1"):
        self.model_id = model_id
        self.llm_mode = llm_mode
        self.prompt_version = prompt_version

    def open(self, world: World, case_id: str, run_id: str, controller: str):
        return ToolSession(world, case_id, run_id, controller, self)


class ToolSession:
    def __init__(self, world, case_id, run_id, controller, factory):
        self.world = world
        self.case_id = case_id
        self.run_id = run_id
        self.controller = controller
        self.factory = factory
        self.step = 0

    def schemas(self) -> list[dict]:
        return schema.tool_json_schemas()

    def call(self, name: str, args: dict) -> schema.ToolEnvelope:
        self.step += 1
        try:
            if name not in schema.TOOL_REGISTRY:
                _fail("unknown_tool", "Tool is not offered in a product session")
            args_type, result_type = schema.TOOL_REGISTRY[name]
            parsed = args_type.model_validate(args)
            if set(args) - set(args_type.model_fields):
                _fail("invalid_args", "Unexpected tool arguments")
            result = getattr(self, "_" + name)(parsed)
            result = result_type.model_validate(result).model_dump(mode="json")
            envelope = schema.ToolEnvelope(ok=True, result=result)
        except ValidationError as exc:
            envelope = schema.ToolEnvelope(
                ok=False, result=None, issues=[GateIssue(code="invalid_args", message=str(exc))]
            )
        except GateError as exc:
            envelope = schema.ToolEnvelope(ok=False, result=None, issues=exc.issues)
        except TransientError:
            envelope = schema.ToolEnvelope(
                ok=False,
                result=None,
                issues=[GateIssue(code="transient", message="Mock system temporarily unavailable")],
            )
        except NeedsHumanError as exc:
            self.world.set_status(self.case_id, status="needs_human", reason=str(exc))
            envelope = schema.ToolEnvelope(
                ok=False, result=None, issues=[GateIssue(code="needs_human", message=str(exc))]
            )
        self.world.trace(
            TraceEvent(
                run_id=self.run_id,
                case_id=self.case_id,
                step=self.step,
                sim_time=self.world.clock.now(),
                kind="tool_call",
                tool=name,
                args=args,
                result=envelope.model_dump(mode="json"),
                result_summary="ok" if envelope.ok else ",".join(i.code for i in envelope.issues),
                observation_sha256=sha256(envelope.model_dump_json().encode()).hexdigest(),
                controller=self.controller,
                model_id=self.factory.model_id,
                llm_mode=self.factory.llm_mode,
            )
        )
        return envelope

    def _evidence(self, evidence_id):
        evidence = self.world.evidence(evidence_id)
        if evidence.case_id != self.case_id:
            _fail("case_scope", "Evidence is outside this session")
        return evidence

    def _citation(self, citation):
        evidence = self._evidence(citation.evidence_id)
        self.world.resolve_citation(citation, self.world.evidence_set_hash(self.case_id))
        if not citation.quote.strip():
            _fail("invalid_citation", "An empty quote is not evidence")
        return evidence

    def _findings(self):
        return run_rules(
            self.world.view(self.case_id).lines,
            self.world.fact_set(self.case_id),
            self.world.ledger(self.case_id),
        )

    def _line(self, line_id):
        line = next(
            (line for line in self.world.view(self.case_id).lines if line.line_id == line_id), None
        )
        if line is None:
            _fail("unknown_line", "Unknown deduction line", line_id)
        return line

    def _list_evidence(self, a):
        docs = (
            self.world.history(self.case_id).evidence_all
            if a.include_superseded
            else self.world.active_evidence(self.case_id)
        )
        return {
            "rows": [
                schema.EvidenceIndexRow(
                    evidence_id=d.evidence_id,
                    doc_ref=d.doc_ref,
                    version=d.version,
                    kind=d.kind,
                    title=d.title,
                    readable=d.readable,
                    method=d.method.value,
                    failure=d.failure.value if d.failure else None,
                    active=d.active,
                    field_keys=list(d.fields),
                    text_chars=len(d.text),
                )
                for d in docs
                if (a.kind is None or d.kind == a.kind)
                and d.available_from <= self.world.clock.now()
            ]
        }

    def _read_evidence(self, a):
        if a.max_chars < 1 or a.max_chars > 100000:
            _fail("invalid_args", "max_chars must be between 1 and 100000")
        doc = self._evidence(a.evidence_id)
        if doc.available_from > self.world.clock.now():
            _fail("unreleased_evidence", "Evidence is not yet released")
        text = doc.text
        if a.locator:
            if a.locator.startswith("fields."):
                key = a.locator.removeprefix("fields.")
                if key not in doc.fields:
                    _fail("invalid_locator", "Unknown field")
                text = _render(doc.fields[key])
            elif a.locator.startswith("page:"):
                page = a.locator.removeprefix("page:")
                if not page.isdecimal() or not 1 <= int(page) <= len(text.split("\f")):
                    _fail("invalid_locator", "Unknown page")
                text = text.split("\f")[int(page) - 1]
            elif a.locator != "text":
                _fail("invalid_locator", "Unsupported read locator")
        facts = [
            f for f in self.world.fact_set(self.case_id).facts if f.evidence_id == doc.evidence_id
        ]
        return dict(
            evidence_id=doc.evidence_id,
            active=doc.active,
            text=text[: a.max_chars],
            truncated=len(text) > a.max_chars,
            source_fields=doc.fields,
            facts=facts,
        )

    def _search_evidence(self, a):
        if not a.query.strip() or not 1 <= a.max_hits <= 100:
            _fail("invalid_args", "Search requires a query and 1–100 hits")
        hits = []
        for doc in self.world.active_evidence(self.case_id):
            index = doc.text.casefold().find(a.query.casefold())
            if index >= 0:
                hits.append(
                    schema.SearchHit(
                        evidence_id=doc.evidence_id,
                        locator="text",
                        snippet=doc.text[max(0, index - 80) : index + len(a.query) + 80],
                    )
                )
        return {"hits": hits[: a.max_hits]}

    def _get_ledger(self, a):
        ledger = self.world.ledger(self.case_id)
        view = self.world.view(self.case_id)
        disputes = {}
        credits = {}
        for entry in ledger:
            if entry.kind == "credit_posted" and entry.line_id:
                credits[entry.line_id] = credits.get(entry.line_id, 0) + entry.amount.cents
        for receipt in view.receipts:
            kind = receipt_kind(receipt, self.case_id)
            if kind in {"dispute", "correction"}:
                for lid, value in allocations(receipt).items():
                    disputes[lid] = disputes.get(lid, 0) + (
                        -value if kind == "correction" else value
                    )
        return dict(
            invoice_total_cents=sum(e.amount.cents for e in ledger if e.kind == "invoice"),
            paid_cents=sum(e.amount.cents for e in ledger if e.kind == "payment"),
            posted_credit_cents=sum(credits.values()),
            open_balance_cents=self.world.ledger_balance(self.case_id).cents,
            lines=[line.model_dump(mode="json") for line in view.lines],
            submitted_dispute_cents_by_line=disputes,
            posted_credit_cents_by_line=credits,
        )

    def _classify_line(self, a):
        self._line(a.line_id)
        doc = self._citation(a.citation)
        trust = doc.method.value if doc.method.value in {"ocr", "vision"} else "model_extracted"
        self.world.set_line_reason(self.case_id, a.line_id, a.reason, trust, a.citation)
        return dict(line_id=a.line_id, reason=a.reason, accepted=True)

    def _propose_fact(self, a):
        doc = self._evidence(a.evidence_id)
        if a.citation.evidence_id != doc.evidence_id:
            _fail("invalid_citation", "Fact citation must reference its evidence")
        self._citation(a.citation)
        if not re.fullmatch(_KEYS.get(doc.kind.value, r"(?!)"), a.key):
            _fail("unknown_fact_key", "Key is outside the evidence vocabulary")
        if not _contains(a.value, a.citation.quote, a.key):
            _fail("fabricated_fact", "Proposed value does not appear in quote")
        if a.key.endswith(("_cents", "_bp")) and type(a.value) is not int:
            _fail("invalid_fact_value", "Money and rates must be integers")
        trust = doc.method.value if doc.method.value in {"ocr", "vision"} else "model_extracted"
        self.world.add_fact(doc.evidence_id, a.key, a.value, trust, a.citation, self.controller)
        return dict(key=a.key, accepted=True, trust=trust)

    def _run_rules(self, a):
        if a.line_ids is not None:
            for lid in a.line_ids:
                self._line(lid)
        return {
            "findings": [
                f for f in self._findings() if a.line_ids is None or f.line_id in a.line_ids
            ]
        }

    def _check_policy(self, a):
        receipts = [
            r
            for r in self.world.view(self.case_id).receipts
            if receipt_kind(r, self.case_id) == "insurer_notice"
        ]
        latest = max(receipts, key=lambda r: (r.at, r.receipt_id), default=None)
        return {"answers": policy.answer(self.world.fact_set(self.case_id), a.question, latest)}

    def _readiness(self, a):
        facts = self.world.fact_set(self.case_id)
        view = self.world.view(self.case_id)
        if a.kind == "dispute":
            if a.line_id is None:
                _fail("line_id_required", "Dispute readiness requires a line")
            line = self._line(a.line_id)
            finding = next(f for f in self._findings() if f.line_id == a.line_id)
            for c in finding.citations:
                self._citation(c)
            result = readiness.dispute(line, finding, facts)
        else:
            if a.line_id is not None:
                _fail("line_id_not_allowed", "Insurance readiness is case-wide")
            inputs = (
                facts,
                self.world.ledger(self.case_id),
                view.receipts,
                self.world.clock.now().date(),
            )
            result = (
                readiness.notice(*inputs, self._findings())
                if a.kind == "notice"
                else readiness.claim(*inputs)
            )
        saved = self.world.save_readiness(result)
        if saved.kind == "notice":
            from recoup.engine.scheduler import schedule_notice

            schedule_notice(self.world, self.case_id)
        return {"readiness": saved}

    def _plan_missing_evidence(self, a):
        if a.line_id is not None:
            self._line(a.line_id)
        items = [
            schema.MissingItem(
                line_id=f.line_id,
                track="deduction",
                need=need,
                why=f.note,
                request_from="internal",
                blocking_for=["dispute", "credit_memo"],
            )
            for f in self._findings()
            if a.line_id is None or f.line_id == a.line_id
            for need in f.missing
        ]
        if a.line_id is None:
            claim = readiness.claim(
                self.world.fact_set(self.case_id),
                self.world.ledger(self.case_id),
                self.world.view(self.case_id).receipts,
                self.world.clock.now().date(),
            )
            if any(d.kind == "insurance_policy" for d in self.world.fact_set(self.case_id).docs):
                items.extend(
                    schema.MissingItem(
                        line_id=None,
                        track="insurance",
                        need=i.requirement,
                        why=i.note,
                        request_from="internal",
                        blocking_for=["claim_package"],
                    )
                    for i in claim.items
                    if i.status in {"missing", "defective", "unknown"}
                )
        return {"items": items}

    def _fetch_from_system(self, a):
        docs = self.world.attach_held(self.case_id, a.system, a.query)
        return dict(
            status="found" if docs else "not_found", new_evidence_ids=[d.evidence_id for d in docs]
        )

    def _propose_decision(self, a):
        findings = {f.line_id: f for f in self._findings()}
        issues = {}
        lines = []
        seen = set()
        for line in a.lines:
            if line.line_id not in findings:
                issues[line.line_id] = [
                    GateIssue(code="unknown_line", message="Unknown deduction line")
                ]
                continue
            if line.line_id in seen:
                issues[line.line_id] = [
                    GateIssue(code="duplicate_line", message="Duplicate decision line")
                ]
                continue
            seen.add(line.line_id)
            finding = findings[line.line_id]
            if line.verdict != finding.verdict:
                issues[line.line_id] = [
                    GateIssue(code="verdict_mismatch", message="Rules own the verdict")
                ]
            for c in line.citations + finding.citations:
                self._citation(c)
            lines.append(
                LineDecision(
                    line_id=line.line_id,
                    verdict=finding.verdict,
                    basis=finding.basis,
                    valid=finding.valid,
                    disputed=finding.disputed,
                    citations=finding.citations,
                    rationale=line.rationale,
                )
            )
        if issues:
            return dict(
                accepted=False, decision_id=None, decision_version=None, per_line_issues=issues
            )
        previous = self.world.current_decision(self.case_id)
        basis_hash = self.world.evidence_set_hash(self.case_id)
        if (
            previous
            and previous.current
            and previous.evidence_set_hash == basis_hash
            and sorted(previous.lines, key=lambda line: line.line_id)
            == sorted(lines, key=lambda line: line.line_id)
        ):
            return dict(
                accepted=True,
                decision_id=previous.decision_id,
                decision_version=previous.version,
                per_line_issues={},
            )
        decision = self.world.save_decision(
            Decision(
                decision_id=previous.decision_id if previous else str(uuid4()),
                case_id=self.case_id,
                version=previous.version + 1 if previous else 1,
                evidence_set_hash=basis_hash,
                lines=lines,
                current=True,
                model_id=self.factory.model_id,
                llm_mode=self.factory.llm_mode,
                prompt_version=self.factory.prompt_version,
                created_at=self.world.clock.now(),
            )
        )
        return dict(
            accepted=True,
            decision_id=decision.decision_id,
            decision_version=decision.version,
            per_line_issues={},
        )

    def _draft_proposal(self, a):
        for lid in a.line_ids:
            self._line(lid)
        if len(set(a.line_ids)) != len(a.line_ids):
            _fail("duplicate_line", "Duplicate requested line")
        if a.kind in {"insurer_notice", "claim_package"}:
            if a.line_ids or a.corrects_receipt_id:
                _fail("line_id_not_allowed", "Insurance packages are case-wide")
            decision = self.world.current_decision(self.case_id)
            if decision is None:
                _fail("stale_decision", "A current decision is required")
            p = Proposal(
                proposal_id=str(uuid4()),
                business_key=f"{self.case_id}:{a.kind.value}:case",
                version=1,
                case_id=self.case_id,
                kind=a.kind,
                target=KIND_TARGET[a.kind],
                recipient=a.recipient,
                amount=None,
                draft_text=a.draft_text,
                draft_sha256=sha256(a.draft_text.encode()).hexdigest(),
                citations=a.citations,
                decision_id=decision.decision_id,
                decision_version=decision.version,
                evidence_set_hash=self.world.evidence_set_hash(self.case_id),
                status="proposed",
                balance_basis=self.world.ledger_balance(self.case_id),
                created_at=self.world.clock.now(),
                created_by="agent",
            )
        else:
            candidates = derive(self.world, self.case_id, a.line_ids)
            p = next(
                (
                    p
                    for p in candidates
                    if p.kind == a.kind
                    and p.corrects_receipt_id == a.corrects_receipt_id
                    and {i.line_id for i in p.allocations} == set(a.line_ids)
                ),
                None,
            )
            if p is None:
                _fail("unsupported_proposal", "No matching proposal derivation")
            p = p.model_copy(
                update=dict(
                    recipient=a.recipient,
                    draft_text=a.draft_text,
                    draft_sha256=sha256(a.draft_text.encode()).hexdigest(),
                    citations=a.citations,
                )
            )
        issues = ProposalValidator().validate(self.world, p, "save")
        if issues:
            return dict(
                accepted=False,
                proposal_id=None,
                version=None,
                business_key=p.business_key,
                amount_cents=p.amount.cents if p.amount else None,
                allocations={},
                issues=issues,
            )
        before = self.world.view(self.case_id).proposals
        saved = self.world.save_proposal(p)
        return dict(
            accepted=True,
            proposal_id=saved.proposal_id,
            version=saved.version,
            business_key=saved.business_key,
            amount_cents=saved.amount.cents if saved.amount else None,
            allocations={i.line_id: i.amount.cents for i in saved.allocations},
            issues=[],
            no_op=any(
                (old.proposal_id, old.version) == (saved.proposal_id, saved.version)
                for old in before
            ),
        )

    def _schedule_followup(self, a):
        days = max(1, min(60, a.days_from_now))
        basis = self.world.evidence_set_hash(self.case_id)
        outbound = [
            r
            for r in self.world.view(self.case_id).receipts
            if receipt_kind(r, self.case_id) in {"dispute", "correction", "follow_up"}
        ]
        if a.kind == "follow_up" and outbound:
            basis = max(outbound, key=lambda r: (r.at, r.receipt_id)).receipt_id
        key = f"{self.case_id}:{a.kind}:{basis}"
        due = self.world.schedule(
            DueWork(
                due_id=str(uuid4()),
                case_id=self.case_id,
                kind=a.kind,
                due_at=self.world.clock.now() + timedelta(days=days),
                basis=basis,
                idempotency_key=key,
            )
        )
        return dict(
            due_id=due.due_id, due_at=due.due_at.isoformat(), clamped=days != a.days_from_now
        )

    def _request_approval(self, a):
        proposal = next(
            (
                p
                for p in self.world.view(self.case_id).proposals
                if (p.proposal_id, p.version) == (a.proposal_id, a.version)
            ),
            None,
        )
        if proposal is None:
            _fail("unknown_proposal", "Proposal version is outside this session")
        issues = ProposalValidator().validate(self.world, proposal, "approve")
        return dict(queued=not issues, issues=issues)

    def _end(self, a):
        return dict(accepted=not (unmet := self.unmet()), unmet=unmet)

    def unmet(self):
        view = self.world.view(self.case_id)
        decision = self.world.current_decision(self.case_id)
        facts = self.world.fact_set(self.case_id)
        if (
            decision is None
            or not decision.current
            or decision.evidence_set_hash != facts.basis_hash
        ):
            return ["current decision"]
        unmet = [
            f"decision:{line.line_id}"
            for line in view.lines
            if line.line_id not in {d.line_id for d in decision.lines}
        ]
        for p in derive(self.world, self.case_id):
            if not any(
                old.business_key == p.business_key
                and old.evidence_set_hash == facts.basis_hash
                and old.status in {"proposed", "approved"}
                for old in view.proposals
            ):
                unmet.append(p.business_key)
        if any(d.kind == "insurance_policy" for d in facts.docs):
            current = [
                r
                for r in self.world.readiness(self.case_id)
                if r.evidence_set_hash == facts.basis_hash and r.status != "stale"
            ]
            if not any(r.kind == "notice" for r in current):
                unmet.append("notice readiness")
            answers = self._check_policy(schema.CheckPolicyArgs(question="claim_window"))["answers"]
            if any(
                answer.computed_date and answer.computed_date <= self.world.clock.now().date()
                for answer in answers
            ):
                if not any(r.kind == "claim" for r in current):
                    unmet.append("claim readiness")
                if not any(
                    p.kind == "claim_package"
                    and p.evidence_set_hash == facts.basis_hash
                    and p.status in {"proposed", "approved", "submitted_mock"}
                    for p in view.proposals
                ):
                    unmet.append("claim package")
        outbound = [
            r
            for r in view.receipts
            if receipt_kind(r, self.case_id) in {"dispute", "correction", "follow_up"}
        ]
        if outbound:
            latest = max(outbound, key=lambda r: (r.at, r.receipt_id))
            if not any(
                w.kind == "follow_up"
                and w.basis == latest.receipt_id
                and w.status in {"pending", "done", "cancelled"}
                for w in view.due
            ):
                unmet.append("follow-up schedule")
        return unmet

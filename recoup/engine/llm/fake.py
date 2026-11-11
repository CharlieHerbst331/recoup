"""Deterministic offline tool policy, not model judgment; design/02 §5.9."""

import json

from recoup.contracts.interfaces import LLMResponse
from recoup.contracts.models import DeductionReason
from recoup.engine.demo_copy import finding_explanation, insurance_text


class FakeLLM:
    mode = "fake"
    model_id = "offline-fakellm"

    def next(self, system, messages, tools):
        observation = json.loads(
            next(m["content"] for m in reversed(messages) if m["role"] == "user")
        )
        results = [(m["name"], json.loads(m["content"])) for m in messages if m["role"] == "tool"]

        def last(name):
            return next((r["result"] for n, r in reversed(results) if n == name and r["ok"]), None)

        def calls(items):
            return LLMResponse(
                model_id=self.model_id,
                mode=self.mode,
                tool_calls=[
                    dict(id=f"fake-{len(results)}-{i}", name=n, arguments=a)
                    for i, (n, a) in enumerate(items)
                ],
            )

        if last("list_evidence") is None:
            return calls([("list_evidence", {})])
        read = {
            r["evidence_id"]
            for n, e in results
            if n == "read_evidence" and e["ok"] and (r := e["result"])
        }
        unread = [r for r in last("list_evidence")["rows"] if r["evidence_id"] not in read]
        if unread:
            return calls([("read_evidence", {"evidence_id": r["evidence_id"]}) for r in unread])
        # Classify only an unambiguous, trusted buyer field naming an actual line (§5.3).
        reasons = {}
        indexes = {row["evidence_id"]: row for row in last("list_evidence")["rows"]}
        for name, envelope in results:
            if name != "read_evidence" or not envelope["ok"]:
                continue
            doc = envelope["result"]
            if indexes.get(doc["evidence_id"], {}).get("kind") != "email":
                continue
            fields = {
                f["key"]: f["value"]
                for f in doc["facts"]
                if f["trust"] in {"source", "human_confirmed"}
            }
            if fields.get("from") not in observation.get("buyer_senders", []):
                continue
            for key, line_id in fields.items():
                if not key.startswith("ded.") or not key.endswith(".line_id"):
                    continue
                prefix = key.removesuffix(".line_id")
                reason = fields.get(prefix + ".reason")
                if reason not in {r.value for r in DeductionReason}:
                    continue
                reasons.setdefault(line_id, {})[reason] = dict(
                    line_id=line_id,
                    reason=reason,
                    citation=dict(
                        evidence_id=doc["evidence_id"],
                        locator="fields." + prefix + ".reason",
                        quote=reason,
                    ),
                )
        classify = []
        for line in observation["case"]["lines"]:
            choices = reasons.get(line["line_id"], {})
            if len(choices) == 1 and line.get("reason") not in choices:
                classify.append(("classify_line", next(iter(choices.values()))))
        if classify:
            return calls(classify)
        findings = last("run_rules")
        if findings is None:
            return calls([("run_rules", {})])
        if not last("propose_decision") or not last("propose_decision")["accepted"]:
            return calls(
                [
                    (
                        "propose_decision",
                        {
                            "lines": [
                                dict(
                                    line_id=f["line_id"],
                                    verdict=f["verdict"],
                                    citations=f["citations"],
                                    rationale=finding_explanation(f),
                                )
                                for f in findings["findings"]
                            ]
                        },
                    )
                ]
            )
        case = observation["case"]
        if observation["has_policy"]:
            done = {
                r["readiness"]["kind"]
                for n, e in results
                if n == "readiness" and e["ok"] and (r := e["result"])
            }
            pending = [k for k in ("notice", "claim") if k not in done]
            if pending:
                return calls([("readiness", {"kind": k}) for k in pending])
            checked = {
                a["question"]
                for m in messages
                if m["role"] == "assistant"
                for c in m.get("tool_calls", [])
                if c["name"] == "check_policy" and (a := c["arguments"])
            }
            # The reviewer profile records a detailed, source-linked policy review.
            # Other offline fixtures retain their existing lightweight tool plan;
            # readiness already applies their structured policy checks (§5.6).
            reviewer_profile = any(
                fact["key"] == "demo_scenario" and fact["value"] == "reviewer-v2"
                for name, envelope in results
                if name == "read_evidence" and envelope["ok"]
                for fact in envelope["result"]["facts"]
            )
            questions = (
                (
                    "applicability",
                    "notice_deadline",
                    "claim_window",
                    "claim_documents",
                    "disputed_debt",
                    "credit_limit",
                    "exclusions",
                )
                if reviewer_profile
                else ("claim_window",)
            )
            if pending_questions := [q for q in questions if q not in checked]:
                return calls([("check_policy", {"question": q}) for q in pending_questions])
        drafts = observation["drafts"][:]
        if observation["insurance_recipients"]:
            existing = {
                p["kind"]
                for p in case["proposals"]
                if p["evidence_set_hash"] == case["decision"]["evidence_set_hash"]
                and p["status"] in {"proposed", "approved", "submitted_mock"}
            }
            receipted = {r["proposal_id"] for r in case["receipts"]}
            existing.update(p["kind"] for p in case["proposals"] if p["proposal_id"] in receipted)
            ready = {r["kind"]: r for r in case["readiness"]}
            kinds = []
            if ready.get("notice", {}).get("status") == "ready":
                kinds.append("insurer_notice")
            # Date comparison is code-owned and supplied as an observation.
            if observation.get("claim_open"):
                kinds.append("claim_package")
            for kind in kinds:
                if kind not in existing:
                    drafts.append(
                        dict(
                            kind=kind,
                            recipient=observation["insurance_recipients"][0],
                            draft_text=insurance_text(
                                case,
                                kind,
                                observation.get("invoice_reference", case["case_id"]),
                                policy_answers=[
                                    answer
                                    for name, envelope in results
                                    if name == "check_policy" and envelope["ok"]
                                    for answer in envelope["result"]["answers"]
                                ],
                            ),
                            citations=[
                                item["policy_citation"]
                                for item in ready.get(
                                    "notice" if kind == "insurer_notice" else "claim", {}
                                ).get("items", [])
                                if item.get("policy_citation")
                            ]
                            + [
                                answer["clause_citation"]
                                for name, envelope in results
                                if name == "check_policy" and envelope["ok"]
                                for answer in envelope["result"]["answers"]
                                if answer.get("clause_citation")
                            ]
                            + [
                                dict(
                                    evidence_id=doc["evidence_id"],
                                    locator="text",
                                    quote=doc["text"],
                                )
                                for name, envelope in results
                                if name == "read_evidence"
                                and envelope["ok"]
                                and (doc := envelope["result"]).get("text")
                                and doc["evidence_id"]
                                in {
                                    eid
                                    for item in ready.get(
                                        "notice" if kind == "insurer_notice" else "claim", {}
                                    ).get("items", [])
                                    for eid in item.get("satisfied_by", [])
                                }
                            ],
                            line_ids=[],
                        )
                    )
        if drafts:
            return calls([("draft_proposal", d) for d in drafts])
        requested = {
            (a["proposal_id"], a["version"])
            for m in messages
            if m["role"] == "assistant"
            for c in m.get("tool_calls", [])
            if c["name"] == "request_approval" and (a := c["arguments"])
        }
        pending = [
            p
            for p in case["proposals"]
            if p["status"] == "proposed" and (p["proposal_id"], p["version"]) not in requested
        ]
        if pending:
            return calls(
                [
                    ("request_approval", dict(proposal_id=p["proposal_id"], version=p["version"]))
                    for p in pending
                ]
            )
        if "follow-up schedule" in observation["unmet"]:
            return calls([("schedule_followup", {"kind": "follow_up", "days_from_now": 14})])
        return calls([("end", {"reason": "Offline policy completed tool work"})])

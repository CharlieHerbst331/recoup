"""Deterministic offline tool policy, not model judgment; design/02 §5.9."""

import json

from recoup.contracts.interfaces import LLMResponse


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
                                    rationale=f["note"],
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
            if last("check_policy") is None:
                return calls([("check_policy", {"question": "claim_window"})])
        drafts = observation["drafts"][:]
        if observation["insurance_recipients"]:
            existing = {
                p["kind"]
                for p in case["proposals"]
                if p["evidence_set_hash"] == case["decision"]["evidence_set_hash"]
                and p["status"] in {"proposed", "approved", "submitted_mock"}
            }
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
                            draft_text=(
                                "SYNTHETIC data. MOCK action. LLM fake. "
                                "Please review the cited evidence."
                            ),
                            citations=[],
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

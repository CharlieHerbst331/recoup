"""Action cards and version history for design/02 §6."""

import re
from difflib import unified_diff
from html import escape

import streamlit as st

from recoup.app import Recoup
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.models import CaseHistory, CaseView, LineAmount, Proposal, ProposalStatus
from recoup.contracts.money import Money, fmt


def proposal_groups(case: CaseView, history: CaseHistory) -> dict[str, list[Proposal]]:
    """Merge snapshots, preferring the view for a matching version."""
    versions = {
        (proposal.proposal_id, proposal.version): proposal
        for proposal in [*history.proposals_all, *case.proposals]
    }
    groups: dict[str, list[Proposal]] = {}
    for proposal in versions.values():
        groups.setdefault(proposal.business_key, []).append(proposal)
    return {
        key: sorted(groups[key], key=lambda proposal: (proposal.version, proposal.proposal_id))
        for key in sorted(groups)
    }


def draft_diff(previous: Proposal, current: Proposal) -> str:
    lines = []
    for line in unified_diff(
        previous.draft_text.splitlines(keepends=True),
        current.draft_text.splitlines(keepends=True),
        fromfile=f"v{previous.version}",
        tofile=f"v{current.version}",
    ):
        lines.append(line.removesuffix("\n"))
        if not line.endswith("\n"):
            lines.append("\\ No newline at end of file")
    return "\n".join(lines)


def _edit_form(proposal: Proposal, key: str) -> bool:
    editable = proposal.status == ProposalStatus.proposed
    with st.expander("Edit proposal"):
        with st.form(f"edit:{key}"):
            st.text_area(
                "Draft text", value=proposal.draft_text, key=f"draft:{key}", disabled=not editable
            )
            st.text_input(
                "Recipient", value=proposal.recipient, key=f"recipient:{key}", disabled=not editable
            )
            for allocation in proposal.allocations:
                # Text inputs preserve cents beyond the browser's safe integer range.
                st.text_input(
                    f"{allocation.line_id} allocation (cents)",
                    value=str(allocation.amount.cents),
                    key=f"allocation:{key}:{allocation.line_id}",
                    disabled=not editable,
                )
            return st.form_submit_button("Save changes", disabled=not editable) and editable


def _edit_changes(proposal: Proposal, key: str) -> dict:
    allocations = []
    for allocation in proposal.allocations:
        value = st.session_state[f"allocation:{key}:{allocation.line_id}"].strip()
        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError(f"{allocation.line_id}: enter a non-negative integer number of cents")
        allocations.append(LineAmount(line_id=allocation.line_id, amount=Money(cents=int(value))))
    return {
        "draft_text": st.session_state[f"draft:{key}"],
        "recipient": st.session_state[f"recipient:{key}"],
        "allocations": allocations,
    }


def _controls(proposal: Proposal, service: Recoup, edit_requested: bool) -> None:
    key = f"{proposal.case_id}:{proposal.proposal_id}:{proposal.version}"
    try:
        if edit_requested:
            changes = _edit_changes(proposal, key)
            with st.spinner("Saving proposal…"):
                service.edit(proposal.proposal_id, proposal.version, **changes)
            st.rerun()

        approve, submit, _ = st.columns([1, 1.5, 2])
        proposed = proposal.status == ProposalStatus.proposed
        if (
            approve.button(
                "Approve draft",
                key=f"approve:{key}",
                disabled=not proposed,
                type="primary",
                width="stretch",
            )
            and proposed
        ):
            with st.spinner("Approving proposal…"):
                service.approve(proposal.proposal_id, proposal.version)
            st.rerun()
        approved = proposal.status == ProposalStatus.approved
        if (
            submit.button("Submit MOCK action", key=f"submit:{key}", disabled=not approved)
            and approved
        ):
            with st.spinner("Submitting MOCK action…"):
                service.submit(proposal.proposal_id, proposal.version)
            st.rerun()

        rejectable = proposal.status in {ProposalStatus.proposed, ProposalStatus.approved}
        with st.expander("Reject this draft"), st.form(f"reject:{key}"):
            reason = st.text_input("Rejection reason", key=f"reason:{key}", disabled=not rejectable)
            rejected = st.form_submit_button("Reject", disabled=not rejectable)
        if rejected and rejectable:
            if not reason.strip():
                st.error("Rejection reason is required.")
            else:
                with st.spinner("Rejecting proposal…"):
                    service.reject(proposal.proposal_id, proposal.version, reason=reason)
                st.rerun()
    except GateError as exc:
        for issue in exc.issues:
            suffix = f" [{issue.line_id}]" if issue.line_id else ""
            st.error(f"{issue.code}{suffix}: {issue.message}")
    except (ValueError, TransientError) as exc:
        st.error(str(exc))


ACTION_NAMES = {
    "dispute": "dispute",
    "credit_memo": "credit",
    "info_request": "information request",
    "follow_up": "follow-up",
    "insurer_notice": "insurer notice",
    "claim_package": "claim package",
    "correction": "correction",
    "counteroffer": "counteroffer",
}
TARGET_NAMES = {
    "mock_buyer_portal": "Buyer portal (MOCK)",
    "mock_erp": "Accounting system (MOCK)",
    "mock_email": "Email (MOCK)",
    "mock_insurer": "Insurer (MOCK)",
}
STATUS_NAMES = {
    "proposed": "Awaiting review",
    "approved": "Approved for MOCK submission",
    "rejected": "Rejected",
    "stale": "Needs a fresh review",
    "cancelled": "Cancelled",
    "submitted_mock": "Submitted to MOCK system",
}


def _action_body(
    current: Proposal, versions: list[Proposal], case: CaseView, service: Recoup, receipts: dict
) -> None:
    amount, recipient, status = st.columns([1, 1.4, 1.3])
    amount.metric("Amount (USD)", fmt(current.amount) if current.amount else "No amount")
    recipient.caption("Recipient")
    recipient.write(TARGET_NAMES[current.target.value])
    status.caption("Status")
    status.html(f'<span class="recoup-state">{escape(STATUS_NAMES[current.status.value])}</span>')
    if current.allocations:
        lines = {line.line_id: line for line in case.lines}
        st.dataframe(
            [
                {
                    "Line": row.line_id,
                    "Reason": (
                        lines[row.line_id].reason.value.replace("_", " ").capitalize()
                        if row.line_id in lines and lines[row.line_id].reason
                        else "Not classified"
                    ),
                    "Amount (USD)": fmt(row.amount),
                    "Response": ("Proposed " if current.status == ProposalStatus.proposed else "")
                    + ACTION_NAMES[current.kind.value],
                }
                for row in current.allocations
            ],
            hide_index=True,
            width="stretch",
        )

    if current.kind == "dispute":
        for proposal in case.proposals:
            if (
                proposal.kind == "credit_memo"
                and proposal.amount is not None
                and proposal.status in {ProposalStatus.proposed, ProposalStatus.approved}
            ):
                st.caption(f"Separate proposed credit: {fmt(proposal.amount)}")

    with st.container(key=f"review-draft-{current.proposal_id}-{current.version}"):
        st.text(current.draft_text)
        key = f"{current.case_id}:{current.proposal_id}:{current.version}"
        edit_requested = _edit_form(current, key)
    if current.status == ProposalStatus.proposed:
        st.caption("Review this version, then approve it before MOCK submission.")
    elif current.status == ProposalStatus.approved:
        st.caption("This version is approved. Submit separately to create a MOCK receipt.")
    elif current.status in {ProposalStatus.stale, ProposalStatus.cancelled}:
        st.warning("This draft is out of date. Run the agent to review the latest evidence.")
    _controls(current, service, edit_requested)

    with st.expander("Sources and action details"):
        st.text(current.business_key)
        st.text(f"Current version: v{current.version} · Status: {current.status.value}")
        st.text(f"Kind: {current.kind.value} · Target: {current.target.value}")
        st.text(f"Recipient: {current.recipient}")
        st.text(f"Amount (USD): {fmt(current.amount) if current.amount else 'None'}")
        if current.citations:
            titles = {row.evidence_id: row.title for row in case.evidence}
            st.dataframe(
                [
                    {
                        "Document": titles.get(row.evidence_id, row.evidence_id),
                        "Source": row.locator,
                        "Quoted evidence": row.quote,
                    }
                    for row in current.citations
                ],
                hide_index=True,
            )
        else:
            st.caption("No citations recorded.")

    with st.expander("Version history"):
        for index, proposal in enumerate(versions):
            st.text(
                f"v{proposal.version} · {proposal.status.value} · "
                f"{proposal.created_by} · {proposal.created_at.isoformat()}"
            )
            st.text(proposal.draft_text)
            if index:
                diff = draft_diff(versions[index - 1], proposal)
                if diff:
                    st.code(diff, language="diff")
                else:
                    st.caption("Draft text unchanged from previous version.")
    for receipt in receipts.values():
        if receipt.business_key == current.business_key:
            st.success(f"{receipt.receipt_id} · {receipt.label}")
            with st.expander("MOCK receipt details"):
                st.json(receipt.model_dump(mode="json"))


def render_actions(case: CaseView, history: CaseHistory, service: Recoup) -> None:
    if history.receipts:
        latest = history.receipts[-1]
        st.success(f"{latest.receipt_id} · {latest.label}")
    groups = proposal_groups(case, history)
    if not groups:
        st.subheader("Review")
        st.info("No actions proposed. Run the agent to review this case.")
        return
    receipts = {receipt.receipt_id: receipt for receipt in [*history.receipts, *case.receipts]}
    priority = {"correction": 0, "dispute": 1, "info_request": 2, "credit_memo": 3}
    ordered = sorted(
        groups.values(),
        key=lambda versions: (
            versions[-1].status not in {ProposalStatus.proposed, ProposalStatus.approved},
            priority.get(versions[-1].kind.value, 4),
            versions[-1].business_key,
        ),
    )
    for index, versions in enumerate(ordered):
        current = versions[-1]
        title = f"Review proposed {ACTION_NAMES[current.kind.value]}"
        if index == 0:
            st.header(title)
            with st.container():
                _action_body(current, versions, case, service, receipts)
        else:
            amount = f" · {fmt(current.amount)}" if current.amount else ""
            with (
                st.expander(f"{ACTION_NAMES[current.kind.value].capitalize()}{amount}"),
                st.container(),
            ):
                _action_body(current, versions, case, service, receipts)

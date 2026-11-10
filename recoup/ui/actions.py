"""Action cards and version history for design/02 §6."""

import re
from difflib import unified_diff

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
            return st.form_submit_button("Edit", disabled=not editable) and editable


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


def _controls(proposal: Proposal, service: Recoup) -> None:
    key = f"{proposal.case_id}:{proposal.proposal_id}:{proposal.version}"
    try:
        if _edit_form(proposal, key):
            changes = _edit_changes(proposal, key)
            with st.spinner("Saving proposal…"):
                service.edit(proposal.proposal_id, proposal.version, **changes)
            st.rerun()

        approve, submit = st.columns(2)
        proposed = proposal.status == ProposalStatus.proposed
        if approve.button("Approve", key=f"approve:{key}", disabled=not proposed) and proposed:
            with st.spinner("Approving proposal…"):
                service.approve(proposal.proposal_id, proposal.version)
            st.rerun()
        approved = proposal.status == ProposalStatus.approved
        if submit.button("Submit", key=f"submit:{key}", disabled=not approved) and approved:
            with st.spinner("Submitting MOCK action…"):
                service.submit(proposal.proposal_id, proposal.version)
            st.rerun()

        rejectable = proposal.status in {ProposalStatus.proposed, ProposalStatus.approved}
        with st.form(f"reject:{key}"):
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


def render_actions(case: CaseView, history: CaseHistory, service: Recoup) -> None:
    st.subheader("Actions")
    st.caption("SYNTHETIC data · MOCK actions · Approval and submission are separate actions.")
    groups = proposal_groups(case, history)
    if not groups:
        st.info("No actions proposed.")
    receipts = {receipt.receipt_id: receipt for receipt in [*history.receipts, *case.receipts]}
    for business_key, versions in groups.items():
        current = versions[-1]
        with st.container(border=True):
            st.text(business_key)
            st.text(f"Current version: v{current.version} · Status: {current.status.value}")
            st.text(f"Kind: {current.kind.value} · Target: {current.target.value}")
            st.text(f"Recipient: {current.recipient}")
            st.text(f"Amount (USD): {fmt(current.amount) if current.amount else 'None'}")
            if current.allocations:
                st.dataframe(
                    [
                        {"Line": row.line_id, "Allocation (cents)": str(row.amount.cents)}
                        for row in current.allocations
                    ],
                    hide_index=True,
                )
            st.text(current.draft_text)
            if current.citations:
                st.dataframe([row.model_dump() for row in current.citations], hide_index=True)
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

            _controls(current, service)
            for receipt in receipts.values():
                if receipt.business_key == business_key:
                    st.success(f"{receipt.receipt_id} · {receipt.label}")
                    st.json(receipt.model_dump(mode="json"))

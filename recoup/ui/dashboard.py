"""Case dashboard presentation from facade snapshots (design/02 §6)."""

from collections import Counter
from collections.abc import Callable

import streamlit as st

from recoup.contracts.models import CaseView, ProposalStatus
from recoup.contracts.money import fmt
from recoup.ui.queue import display_title, format_case, next_due_at

FILTERS = ("All cases", "Needs approval", "Approved", "MOCK submitted", "Needs attention")


def approval_count(case: CaseView) -> int:
    return sum(row.status == ProposalStatus.proposed for row in case.proposals)


def approved_count(case: CaseView) -> int:
    return sum(row.status == ProposalStatus.approved for row in case.proposals)


def needs_attention(case: CaseView) -> bool:
    return (
        case.status in {"needs_info", "needs_human"}
        or any(row.status == "not_ready" for row in case.readiness)
        or any(row.status == ProposalStatus.stale for row in case.proposals)
    )


def case_tags(case: CaseView) -> list[tuple[str, str]]:
    """Display recorded statuses; approval is separate from submission gates."""
    tags = []
    if count := approval_count(case):
        tags.append((f"Needs approval · {count}", "orange"))
    if count := approved_count(case):
        tags.append((f"Approved · {count}", "blue"))
    if case.receipts:
        tags.append((f"MOCK submitted · {len(case.receipts)}", "green"))
    if case.status == "needs_human":
        tags.append(("Human review needed", "red"))
    if case.status == "needs_info":
        tags.append(("Needs information", "violet"))
    if any(row.status == "not_ready" for row in case.readiness):
        tags.append(("Checklist gaps", "gray"))
    if any(row.status == ProposalStatus.stale for row in case.proposals):
        tags.append(("Outdated draft", "gray"))
    return tags or [(case.status.value.replace("_", " ").capitalize(), "gray")]


def filter_cases(cases: list[CaseView], category: str, query: str) -> list[CaseView]:
    query = query.strip().casefold()
    return [
        case
        for case in cases
        if (
            category == "All cases"
            or (category == "Needs approval" and approval_count(case))
            or (category == "Approved" and approved_count(case))
            or (category == "MOCK submitted" and case.receipts)
            or (category == "Needs attention" and needs_attention(case))
        )
        and query in f"{case.case_id} {case.buyer} {case.title}".casefold()
    ]


def dashboard_counts(cases: list[CaseView]) -> dict[str, int]:
    return {
        "Cases": len(cases),
        "Need approval": sum(bool(approval_count(case)) for case in cases),
        "Approved cases": sum(bool(approved_count(case)) for case in cases),
        "MOCK submitted": sum(bool(case.receipts) for case in cases),
    }


def demo_next_step(cases: list[CaseView]) -> str:
    case = next((case for case in cases if case.case_id == "H"), None)
    if case is None:
        return "Load the demo cases to start the walkthrough."
    if any(row.kind == "correction" and row.status == "proposed" for row in case.proposals):
        return "Review H’s new correction, then compare POD v1 and v2 in Documents."
    dispute = next((row for row in case.proposals if row.kind == "dispute"), None)
    if dispute is not None and dispute.status == "approved":
        return "Submit H’s approved dispute to create a MOCK receipt."
    if dispute is not None and dispute.status == "submitted_mock":
        return "Advance to next due in the Simulation lab to release the next scheduled event."
    return "Open H, edit its dispute draft, and approve the revised version."


def _case_card(case: CaseView, open_case: Callable[[str], None]) -> None:
    with st.container(border=True, key=f"hub-case-{case.case_id}"):
        customer, balance = st.columns([3, 1])
        customer.subheader(case.buyer)
        customer.caption(f"Case {case.case_id} · {display_title(case.title)}")
        balance.write(f"**{fmt(case.open_balance)}**")
        balance.caption("Open balance · USD")
        with st.container(horizontal=True, gap="small"):
            for label, color in case_tags(case):
                st.badge(label, color=color)
        counts = Counter(
            row.kind.value.replace("_", " ")
            for row in case.proposals
            if row.status in {"proposed", "approved"}
        )
        if counts:
            st.caption(
                "Pending actions: "
                + ", ".join(f"{kind} ({count})" for kind, count in counts.items())
            )
        due = next_due_at(case)
        st.caption(
            f"Next scheduled work: {due.strftime('%b %d, %Y · %H:%M UTC')}"
            if due
            else "No pending scheduled work."
        )
        st.button(
            f"Review case {case.case_id}" if approval_count(case) else f"Open case {case.case_id}",
            key=f"open-case:{case.case_id}",
            on_click=open_case,
            args=(case.case_id,),
            width="stretch",
        )


def render_dashboard(
    cases: list[CaseView], open_case: Callable[[str], None], start_simulation: Callable[[], None]
) -> None:
    st.title("Case dashboard")
    st.caption("Review outgoing work, spot approvals, and follow each case through the simulation.")
    with st.container(key="hub-metrics"):
        for column, (label, value) in zip(
            st.columns(4), dashboard_counts(cases).items(), strict=True
        ):
            column.metric(label, value)

    with st.container(border=True, key="simulation-guide"):
        intro, start = st.columns([3, 1])
        intro.subheader("Test the workflow")
        intro.write(demo_next_step(cases))
        intro.caption(
            "1. Load H, C and N.  2. Edit and approve H.  "
            "3. Submit a MOCK action.  4. Advance to next due."
        )
        start.button(
            "Start fresh simulation",
            key="start_simulation",
            on_click=start_simulation,
            width="stretch",
        )
        st.caption(
            "A fresh simulation uses a new database and keeps your current run. "
            "The Simulation lab in the sidebar controls time for all loaded cases."
        )
        if any(case.case_id == "H" for case in cases):
            st.button("Open demo case H", on_click=open_case, args=("H",), key="open_demo_h")

    st.subheader("Outgoing cases")
    st.caption(
        "Tags reflect current drafts and MOCK receipts. "
        "Approved drafts still pass the service’s checks at submission."
    )
    query = st.text_input(
        "Search cases", placeholder="Customer, case ID, or issue", key="case_search"
    )
    category = st.pills(
        "Show cases", FILTERS, default="All cases", required=True, key="case_filter"
    )
    visible = filter_cases(cases, category, query)
    st.caption(f"Showing {len(visible)} of {len(cases)} cases")
    if not cases:
        st.info(
            "No cases loaded. Load demo cases in the Simulation lab "
            "or start a fresh simulation above."
        )
    elif not visible:
        st.info("No cases match these filters. Choose All cases or clear your search.")
    for case in visible:
        _case_card(case, open_case)
    if cases:
        with st.expander("Table view"):
            st.dataframe(
                [
                    {
                        "Case": case.case_id,
                        "Customer": case.buyer,
                        "Issue": display_title(case.title),
                        "Tags": "; ".join(label for label, _ in case_tags(case)),
                        "Open balance (USD)": fmt(case.open_balance),
                        "Next due": format_case(case)["Next due (UTC)"],
                    }
                    for case in visible
                ],
                hide_index=True,
                width="stretch",
            )

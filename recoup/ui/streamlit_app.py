"""Run with streamlit run recoup/ui/streamlit_app.py (design/02 §6)."""

import sqlite3
from html import escape
from pathlib import Path
from uuid import uuid4

import streamlit as st

from recoup.app import Recoup, RecoupConfig, build
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.money import fmt
from recoup.ui.case_page import render_case
from recoup.ui.dashboard import approval_count, approved_count, render_dashboard
from recoup.ui.queue import (
    case_label,
    format_clock,
    format_quarantine,
    sort_cases,
)

DEMO_ROOT = Path(__file__).resolve().parents[2] / "cases" / "demo"


def _sidebar_controls(service: Recoup, selected: str | None, lab) -> None:
    with lab:
        st.write(
            f"**Day {service.world.clock.day()} · {service.world.clock.now().date():%b %d, %Y}**"
        )
        due_day = service.next_due_day()
        st.caption(
            f"Next due: day {due_day}" if due_day is not None else "Next due: none scheduled."
        )
        if st.button(
            "Advance to next due",
            key="advance_next_due",
            disabled=due_day is None,
            type="primary",
            width="stretch",
            help="Move all cases to the next scheduled event or due task, then run the agent.",
        ):
            with st.spinner("Advancing to next due…"):
                service.advance(to_next_due=True)
            _refresh(
                "Simulation advanced to the next due item. Check updated drafts and checklists."
            )
        st.caption(
            "Advancing time releases scheduled evidence and runs the agent "
            "automatically for all cases."
        )
        with st.expander("Advance a specific number of days"):
            days = st.number_input("Days", min_value=1, value=1, step=1, key="advance_days")
            if st.button("Advance N days", key="advance_n_days", width="stretch"):
                with st.spinner(f"Advancing {days} days…"):
                    service.advance(days=days)
                _refresh(f"Advanced {days} days. All loaded cases have been refreshed.")
        if st.button("Run agent", key="run_agent", disabled=selected is None, width="stretch"):
            with st.spinner(f"Running agent for case {selected}…"):
                service.run(selected)
            _refresh(f"Agent finished reviewing case {selected}.")
        st.caption(
            f"Run agent reviews case {selected}." if selected else "Open a case to run its agent."
        )


def _refresh(message: str) -> None:
    st.session_state.simulation_notice = message
    st.rerun()


def _open_case(case_id: str) -> None:
    st.session_state.selected_case = case_id


def _start_simulation() -> None:
    st.session_state.db_path = f"runs/simulation-{uuid4().hex}.db"
    st.session_state.selected_case = None
    st.session_state.case_search = ""
    st.session_state.case_filter = "All cases"
    st.session_state.start_demo = True


def _style() -> None:
    # Native widgets keep keyboard behavior; these selectors only change presentation.
    st.html("""<style>
    :root { --recoup-lime: #e4f222; }
    html, body, [data-testid="stApp"] { font-family: Arial, Helvetica, sans-serif; }
    h1, h2, h3, p, button, input, textarea, label {
        font-family: Arial, Helvetica, sans-serif !important;
    }
    h1 { font-size: 1.85rem !important; font-weight: 650 !important; letter-spacing: -.04rem; }
    h2 { font-size: 1.5rem !important; font-weight: 650 !important; }
    h3 { font-size: 1.15rem !important; font-weight: 600 !important; }
    [data-testid="stMainBlockContainer"] { padding: 2rem 2.5rem 4rem; max-width: 1600px; }
    [data-testid="stSidebar"]:not([data-collapsed="true"]) {
        min-width: 290px; max-width: 320px;
    }
    [data-testid="stSidebarHeader"] { height: 0; min-height: 0; }
    [data-testid="stSidebarUserContent"] { padding: .4rem 0; }
    [data-testid="stSidebar"] h1 { font-size: 1.8rem !important; margin-bottom: .75rem; }
    .stAppDeployButton { display: none; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMetricValue"] { font-size: 1.65rem; font-weight: 600; }
    [data-testid="stMetricLabel"] { color: #62625c; }
    .st-key-invoice-total [data-testid="stMetricValue"] { font-size: 1.2rem; font-weight: 400; }
    button { border-radius: 6px !important; font-size: .9rem !important; }
    button[kind="primary"] { background: #191919; color: white; border-color: #191919; }
    button[kind="primary"]:hover { background: #363630; border-color: #363630; }
    button:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 3px solid #858b16 !important; outline-offset: 3px;
    }
    button:disabled { opacity: .5; }
    .st-key-selected_case [role="radiogroup"] { gap: 0; width: 100%; }
    .st-key-selected_case [data-testid="stRadioGroup"] > div {
        width: 100%; box-sizing: border-box;
        padding: .85rem .7rem; border-bottom: 1px solid #e4e4df;
        border-left: 3px solid transparent;
    }
    .st-key-selected_case [data-testid="stRadioGroup"] > div[data-selected="true"] {
        background: #f4f6d9; border-left-color: #c5d20c;
    }
    .st-key-selected_case [data-testid="stRadioOption"] { padding: 0; margin: 0; width: 100%; }
    .st-key-selected_case [data-testid="stRadioOption"] > div > div:first-child { display: none; }
    .st-key-selected_case [data-testid="stRadioOption"] > div { padding: 0; }
    .st-key-selected_case [data-testid="stRadioGroup"] > div:has(input:focus-visible) {
        outline: 2px solid #858b16; outline-offset: -2px;
    }
    .st-key-selected_case p { font-size: .9rem; line-height: 1.5; }
    .st-key-selected_case [data-testid="stRadioCaption"] { margin-left: 0; padding-left: 0; }
    [role="tablist"] { gap: 1.8rem; border-bottom: 1px solid #e4e4df; margin: .5rem 0 .8rem; }
    [role="tab"] { padding: .75rem 0; font-size: 1rem !important; }
    [role="tab"][aria-selected="true"] { color: #191919; font-weight: 600; }
    [data-baseweb="tab-highlight"] { background-color: #191919; }
    .recoup-provenance {
        display: flex; align-items: center; flex-wrap: wrap; gap: .5rem 1rem;
        font-size: .8rem; color: #60605a; padding-bottom: 1.2rem;
        border-bottom: 1px solid #e4e4df; margin-bottom: .5rem;
    }
    .st-key-hub-metrics [data-testid="stMetric"] {
        background: #f5f5f2; border: 1px solid #e4e4df;
        border-radius: 8px; padding: .75rem 1rem;
    }
    .st-key-simulation-guide { background: #f9faed; }
    [class*="st-key-hub-case-"] h3 { margin-bottom: 0; }
    .st-key-simulation-lab { background: #f2f4df; }
    .recoup-provenance strong { color: #191919; background: #f1f4c3; padding: .25rem .5rem; }
    .recoup-provenance span { white-space: normal; }
    .recoup-state { display: inline-block; padding: .3rem .65rem; border-radius: 16px;
        background: #f0f2cb; color: #343623; font-size: .88rem; }
    [class*="st-key-review-draft"] [data-testid="stText"] {
        font-family: Arial, Helvetica, sans-serif; white-space: pre-wrap; line-height: 1.6;
    }
    [class*="st-key-review-draft"] { background: #f7f7f4; padding: 1rem; border-radius: 6px; }
    @media (max-width: 850px) {
        [data-testid="stHeader"] { background: #ffffff; }
        [data-testid="stMainBlockContainer"] { padding: 4rem 1rem 3rem; }
        h1 { font-size: 1.5rem !important; }
        .recoup-provenance { gap: .4rem .7rem; margin-bottom: 1rem; }
        .st-key-hub-metrics [data-testid="stHorizontalBlock"] {
            flex-direction: row; flex-wrap: wrap; gap: .5rem;
        }
        .st-key-hub-metrics [data-testid="stColumn"] {
            flex: 1 1 calc(50% - .5rem); min-width: calc(50% - .5rem);
            width: calc(50% - .5rem);
        }
    }
    </style>""")


def _provenance(service: Recoup, config: RecoupConfig) -> None:
    clock = escape(format_clock(service.world.clock.day(), service.world.clock.now()))
    st.html(
        '<div class="recoup-provenance" role="note" aria-label="Demo provenance">'
        "<strong>SYNTHETIC DATA</strong><span>MOCK actions</span>"
        f"<span>LLM: {escape(config.llm)}</span><span>{clock}</span>"
        "<span>MOCK ACKNOWLEDGMENT — not sent to any real system</span>"
        "<span>Cash collected: $0.00</span></div>"
    )


def main() -> None:
    st.set_page_config(
        page_title="Recoup · Dashboard", layout="wide", initial_sidebar_state="expanded"
    )
    _style()
    st.sidebar.title("Recoup")
    st.sidebar.caption("Case workbench")
    st.sidebar.button("Dashboard", key="dashboard_home", on_click=_clear_case, width="stretch")
    navigation = st.sidebar.container()
    lab = st.sidebar.container(border=True, key="simulation-lab")
    with lab:
        st.subheader("Simulation lab")
        st.caption("Test with SYNTHETIC cases and MOCK actions. Nothing is sent externally.")
        load_demo = st.button("Load demo cases H, C and N", key="load_demo", width="stretch")
    with st.sidebar.expander("Database settings"):
        db = st.text_input(
            "Database path", value="runs/demo.db", key="db_path", on_change=_clear_case
        )

    try:
        config = RecoupConfig.from_env().model_copy(update={"db": db})
        service = build(config)
        try:
            if load_demo or st.session_state.pop("start_demo", False):
                with st.spinner("Loading SYNTHETIC demo cases…"):
                    results = service.load(
                        [str(DEMO_ROOT / case_id) for case_id in ("H", "C", "N")]
                    )
                for result in results:
                    lab.info(
                        f"{result.case_id}: {result.status}"
                        + (f" — {result.reason}" if result.reason else "")
                    )

            _provenance(service, config)
            if notice := st.session_state.pop("simulation_notice", None):
                st.success(notice)
            cases = sort_cases(service.world.list_cases())
            by_id = {case.case_id: case for case in cases}
            with navigation:
                st.subheader(f"Cases ({len(cases)})")
                selected = st.radio(
                    "Open case",
                    options=list(by_id),
                    index=None,
                    format_func=lambda case_id: case_label(by_id[case_id]),
                    captions=[
                        f"{fmt(case.open_balance)} · Case {case.case_id}"
                        + (
                            f" · Needs approval ({approval_count(case)})"
                            if approval_count(case)
                            else ""
                        )
                        + (f" · Approved ({approved_count(case)})" if approved_count(case) else "")
                        for case in cases
                    ],
                    key="selected_case",
                    label_visibility="collapsed",
                    width="stretch",
                )
            _sidebar_controls(service, selected, lab)
            if selected is not None:
                render_case(service.world.view(selected), service.history(selected), service)
                return

            render_dashboard(cases, _open_case, _start_simulation)

            st.subheader("Imports needing attention")
            quarantined = service.world.list_quarantined()
            if quarantined:
                st.dataframe([format_quarantine(record) for record in quarantined], hide_index=True)
            else:
                st.caption("No imports need attention.")
        finally:
            close = getattr(service.world, "close", None)
            if close is not None:
                close()
    except GateError as exc:
        for issue in exc.issues:
            suffix = f" [{issue.line_id}]" if issue.line_id else ""
            st.error(f"{issue.code}{suffix}: {issue.message}")
    except (
        TransientError,
        OSError,
        ValueError,
        LookupError,
        NotImplementedError,
        ImportError,
        sqlite3.Error,
    ) as exc:
        st.error(f"Error: {exc}")


def _clear_case() -> None:
    st.session_state.selected_case = None


if __name__ == "__main__":
    main()

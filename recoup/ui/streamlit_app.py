"""Run with streamlit run recoup/ui/streamlit_app.py (design/02 §6)."""

import sqlite3
from html import escape
from pathlib import Path

import streamlit as st

from recoup.app import Recoup, RecoupConfig, build
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.money import fmt
from recoup.ui.case_page import render_case
from recoup.ui.queue import (
    case_label,
    display_title,
    format_case,
    format_clock,
    format_quarantine,
    sort_cases,
)

DEMO_ROOT = Path(__file__).resolve().parents[2] / "cases" / "demo"


def _sidebar_controls(service: Recoup, selected: str | None) -> None:
    with st.sidebar.expander("Simulation controls"):
        st.divider()
        st.caption("Simulation")
        days = st.number_input("Days", min_value=1, value=1, step=1, key="advance_days")
        if st.button("Advance N days", key="advance_n_days"):
            with st.spinner(f"Advancing {days} days…"):
                service.advance(days=days)
            st.rerun()

        due_day = service.next_due_day()
        st.caption(
            f"Next due: day {due_day}" if due_day is not None else "Next due: none scheduled."
        )
        if st.button("Advance to next due", key="advance_next_due", disabled=due_day is None):
            with st.spinner("Advancing to next due…"):
                service.advance(to_next_due=True)
            st.rerun()

        if st.button("Run agent", key="run_agent", disabled=selected is None):
            with st.spinner(f"Running agent for case {selected}…"):
                service.run(selected)
            st.rerun()


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
    }
    </style>""")


def _provenance(service: Recoup, config: RecoupConfig) -> None:
    clock = escape(format_clock(service.world.clock.day(), service.world.clock.now()))
    st.html(
        '<div class="recoup-provenance" role="note" aria-label="Demo provenance">'
        "<strong>SYNTHETIC DATA</strong><span>MOCK actions</span>"
        f"<span>LLM: {escape(config.llm)}</span><span>{clock}</span>"
        "<span>Not sent to any real system · Cash collected: $0.00</span></div>"
    )


def main() -> None:
    st.set_page_config(page_title="Recoup · Cases", layout="wide", initial_sidebar_state="expanded")
    _style()
    st.sidebar.title("Recoup")
    navigation = st.sidebar.container()
    with st.sidebar.expander("Demo controls"):
        db = st.text_input(
            "Database path", value="runs/demo.db", key="db_path", on_change=_clear_case
        )
        load_demo = st.button("Load demo cases H, C and N", key="load_demo")

    try:
        config = RecoupConfig.from_env().model_copy(update={"db": db})
        service = build(config)
        try:
            if load_demo:
                with st.spinner("Loading SYNTHETIC demo cases…"):
                    results = service.load(
                        [str(DEMO_ROOT / case_id) for case_id in ("H", "C", "N")]
                    )
                for result in results:
                    st.sidebar.info(
                        f"{result.case_id}: {result.status}"
                        + (f" — {result.reason}" if result.reason else "")
                    )

            _provenance(service, config)
            cases = sort_cases(service.world.list_cases())
            by_id = {case.case_id: case for case in cases}
            with navigation:
                st.subheader(f"Cases ({len(cases)})")
                selected = st.radio(
                    "Open case",
                    options=list(by_id),
                    index=None,
                    format_func=lambda case_id: case_label(by_id[case_id]),
                    captions=[f"{fmt(case.open_balance)} · Case {case.case_id}" for case in cases],
                    key="selected_case",
                    label_visibility="collapsed",
                    width="stretch",
                )
            _sidebar_controls(service, selected)
            if selected is not None:
                navigation.button("Back to queue", on_click=_clear_case, type="tertiary")
                render_case(service.world.view(selected), service.history(selected), service)
                return

            st.title("Cases")
            st.caption("Sorted by earliest pending due date, then highest open balance.")
            if cases:
                rows = [format_case(case) for case in cases]
                st.dataframe(
                    [
                        {
                            "Case": row["Case"],
                            "Customer": row["Buyer"],
                            "Issue": display_title(row["Title"]),
                            "Open balance (USD)": row["Open balance (USD)"],
                            "Next due": row["Next due (UTC)"],
                        }
                        for row in rows
                    ],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No cases loaded. Use the sidebar to load the SYNTHETIC demo cases.")

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

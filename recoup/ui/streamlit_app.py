"""Run with streamlit run recoup/ui/streamlit_app.py (design/02 §6)."""

import sqlite3
from pathlib import Path

import streamlit as st

from recoup.app import Recoup, RecoupConfig, build
from recoup.contracts.interfaces import GateError, TransientError
from recoup.ui.case_page import render_case
from recoup.ui.queue import format_case, format_clock, format_quarantine, sort_cases

DEMO_ROOT = Path(__file__).resolve().parents[2] / "cases" / "demo"


def _sidebar_controls(service: Recoup, selected: str | None) -> None:
    with st.sidebar:
        st.subheader("Demo controls")
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


def main() -> None:
    st.set_page_config(page_title="Recoup · SYNTHETIC AR queue", layout="wide")
    db = st.sidebar.text_input(
        "Database path", value="runs/demo.db", key="db_path", on_change=_clear_case
    )
    load_demo = st.sidebar.button("Load demo cases H, C and N", key="load_demo")

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

            clock, llm, provenance = st.columns([3, 1, 1])
            clock.info(format_clock(service.world.clock.day(), service.world.clock.now()))
            llm.info(f"LLM: {config.llm}")
            provenance.warning("SYNTHETIC DATA")

            st.caption("MOCK actions · Cash collected: $0.00")
            st.caption("MOCK ACKNOWLEDGMENT — not sent to any real system")
            cases = sort_cases(service.world.list_cases())
            selected = st.selectbox(
                "Open case",
                options=[case.case_id for case in cases],
                index=None,
                placeholder="Pick a case from the queue",
                key="selected_case",
            )
            _sidebar_controls(service, selected)
            if selected is not None:
                st.button("Back to queue", on_click=_clear_case)
                render_case(service.world.view(selected), service.history(selected), service)
                return

            st.title("Recoup case queue")
            st.caption("Sorted by earliest pending due date, then highest open balance.")
            if cases:
                st.dataframe([format_case(case) for case in cases], hide_index=True)
            else:
                st.info("No cases loaded. Use the sidebar to load the SYNTHETIC demo cases.")

            st.subheader("Quarantined bundles")
            quarantined = service.world.list_quarantined()
            if quarantined:
                st.dataframe([format_quarantine(record) for record in quarantined], hide_index=True)
            else:
                st.info("No quarantined bundles.")
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

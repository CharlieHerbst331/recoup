"""Case page for design/02 §6."""

import streamlit as st

from recoup.app import Recoup
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import CaseHistory, CaseView, Citation
from recoup.ui.actions import render_actions
from recoup.ui.case import group_readiness, money_table, timeline_rows
from recoup.ui.evidence import evidence_fields, evidence_rows, evidence_versions, inject_document


def _citations(citations: list[Citation]) -> None:
    if citations:
        st.dataframe(
            [citation.model_dump() for citation in citations],
            hide_index=True,
        )
    else:
        st.caption("No citations recorded.")


def _gate_errors(exc: GateError) -> None:
    for issue in exc.issues:
        st.error(f"{issue.code}: {issue.message}")


def _evidence(case: CaseView, history: CaseHistory, service: Recoup) -> None:
    st.subheader("Evidence")
    versions = evidence_versions(case, history)
    if versions:
        st.dataframe(evidence_rows(versions), hide_index=True)
    else:
        st.info("No evidence recorded.")
    for row in versions:
        st.text(f"{row.doc_ref} v{row.version} · {row.title} · {row.evidence_id}")
        fields = evidence_fields(row, history)
        if fields:
            st.dataframe(fields, hide_index=True)
        else:
            st.caption("No fields recorded.")
        for field in fields:
            if field["field_trust"] in {"ocr", "vision"}:
                label, action = st.columns([4, 1])
                label.text(f"{field['field']}: {field['value']} · {field['field_trust']}")
                if action.button(
                    "Confirm", key=f"confirm:{case.case_id}:{row.evidence_id}:{field['field']}"
                ):
                    try:
                        service.confirm_field(row.evidence_id, field["field"])
                    except GateError as exc:
                        _gate_errors(exc)
                    else:
                        st.rerun()

    with st.form(f"inject:{case.case_id}"):
        st.subheader("Inject document")
        st.caption("SYNTHETIC data · BundleDoc JSON · optional document file")
        document_json = st.text_area("BundleDoc JSON", key=f"document-json:{case.case_id}")
        upload = st.file_uploader("Document file (optional)", key=f"document-file:{case.case_id}")
        submitted = st.form_submit_button("Inject document")
    if submitted:
        try:
            inject_document(
                service,
                case.case_id,
                document_json,
                upload.name if upload is not None else None,
                upload.getvalue() if upload is not None else None,
            )
        except GateError as exc:
            _gate_errors(exc)
        except (ValueError, OSError) as exc:
            st.error(f"Invalid document: {exc}")
        else:
            st.rerun()


def render_case(case: CaseView, history: CaseHistory, service: Recoup) -> None:
    st.title(f"Case {case.case_id}: {case.title}")
    st.text(f"Buyer: {case.buyer}")
    status, insurance = st.columns(2)
    status.info(f"Status: {case.status.value}")
    insurance.info(f"Insurance: {case.insurance.value}")
    st.text(f"Status reason: {case.status_reason or 'No reason recorded.'}")

    st.subheader("Money (USD)")
    st.dataframe(money_table(case), hide_index=True)

    _evidence(case, history, service)

    st.subheader("Line decisions")
    decisions = {line.line_id: line for line in case.decision.lines} if case.decision else {}
    if case.decision:
        st.caption(
            f"Decision v{case.decision.version} · LLM: {case.decision.llm_mode} "
            f"({case.decision.model_id}) · current={case.decision.current}"
        )
    for line in case.lines:
        st.text(f"Line {line.line_id}")
        decision = decisions.get(line.line_id)
        if decision is None:
            st.caption("No decision recorded.")
            continue
        st.text(f"Basis: {decision.basis.value}")
        st.text(decision.rationale)
        _citations(decision.citations)
    if not case.lines:
        st.info("No deduction lines.")

    render_actions(case, history, service)

    st.subheader("Readiness")
    for kind, records in group_readiness(case).items():
        with st.expander(kind.capitalize(), expanded=True):
            if not records:
                st.caption("No readiness assessment recorded.")
            for record in records:
                st.text(f"{record.readiness_id} · {record.line_id or 'Case'} · {record.status}")
                if record.deadline is not None:
                    st.text(f"Deadline: {record.deadline.isoformat()}")
                if record.deadline_citation is not None:
                    _citations([record.deadline_citation])
                for item in record.items:
                    st.text(f"{item.item_id}: {item.requirement} · {item.status}")
                    if item.note:
                        st.text(item.note)
                    if item.satisfied_by:
                        st.text(f"Satisfied by: {', '.join(item.satisfied_by)}")
                    if item.policy_citation is not None:
                        _citations([item.policy_citation])

    st.subheader("Timeline")
    rows = timeline_rows(history)
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info("No history recorded.")

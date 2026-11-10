"""Case page for design/02 §6."""

import streamlit as st

from recoup.app import Recoup
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import CaseHistory, CaseView, Citation
from recoup.contracts.money import fmt
from recoup.ui.actions import render_actions
from recoup.ui.case import group_readiness, money_table, timeline_rows
from recoup.ui.evidence import evidence_fields, evidence_rows, evidence_versions, inject_document
from recoup.ui.queue import display_title


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
    st.subheader("Documents")
    st.caption("SYNTHETIC source documents, including earlier versions.")
    versions = evidence_versions(case, history)
    if not versions:
        st.info("No evidence recorded.")
    for row in versions:
        state = "Current" if row.active else "Superseded"
        with st.expander(f"{display_title(row.title)} · v{row.version} · {state}"):
            st.text(f"{row.doc_ref} v{row.version} · {row.title} · {row.evidence_id}")
            st.caption(
                f"{row.kind.value.replace('_', ' ').capitalize()} · "
                f"{'Readable' if row.readable else 'Not readable'} · "
                f"{row.method.value.replace('_', ' ')}"
            )
            if row.failure:
                st.warning(f"Document processing: {row.failure.value.replace('_', ' ')}")
            fields = evidence_fields(row, history)
            if fields:
                st.dataframe(fields, hide_index=True, width="stretch")
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
    with st.expander("Document import details"):
        st.dataframe(evidence_rows(versions), hide_index=True)

    with st.expander("Add supporting document"), st.form(f"inject:{case.case_id}"):
        st.caption("SYNTHETIC data · Describe the document in BundleDoc JSON format.")
        document_json = st.text_area(
            "Document description (JSON)", key=f"document-json:{case.case_id}"
        )
        upload = st.file_uploader("Document file (optional)", key=f"document-file:{case.case_id}")
        submitted = st.form_submit_button("Add document")
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


def _assessment(case: CaseView) -> None:
    st.subheader("Deduction review")
    st.dataframe(money_table(case), hide_index=True, width="stretch")
    decisions = {line.line_id: line for line in case.decision.lines} if case.decision else {}
    if case.decision:
        st.caption(
            f"Decision v{case.decision.version} · LLM: {case.decision.llm_mode} "
            f"({case.decision.model_id}) · "
            f"{'Current assessment' if case.decision.current else 'Earlier assessment'}"
        )
    for line in case.lines:
        reason = line.reason.value.replace("_", " ").capitalize() if line.reason else "Unclassified"
        st.write(f"**{line.line_id} · {reason}**")
        decision = decisions.get(line.line_id)
        if decision is None:
            st.caption("No decision recorded.")
            continue
        st.text(f"Basis: {decision.basis.value}")
        st.text(decision.rationale)
        _citations(decision.citations)
    if not case.lines:
        st.info("No deduction lines.")


def _readiness(case: CaseView) -> None:
    for kind, records in group_readiness(case).items():
        with st.expander(kind.capitalize()):
            if not records:
                st.caption("No readiness assessment recorded.")
            for record in records:
                st.text(f"{record.readiness_id} · {record.line_id or 'Case'} · {record.status}")
                if record.deadline is not None:
                    st.write(f"Deadline: {record.deadline.isoformat()}")
                if record.deadline_citation is not None:
                    _citations([record.deadline_citation])
                for item in record.items:
                    st.write(
                        f"**{item.requirement.replace('_', ' ').replace('.', ' ')}** · "
                        f"{item.status.replace('_', ' ')}"
                    )
                    if item.note:
                        st.write(item.note)
                    if item.satisfied_by:
                        titles = {
                            row.evidence_id: display_title(row.title) for row in case.evidence
                        }
                        st.caption(
                            "Source: "
                            + ", ".join(titles.get(ref, ref) for ref in item.satisfied_by)
                        )
                    if item.policy_citation is not None:
                        _citations([item.policy_citation])


def render_case(case: CaseView, history: CaseHistory, service: Recoup) -> None:
    heading, balance, total = st.columns([2.2, 1, 1])
    heading.title(case.buyer)
    invoice = next(
        (
            row.fields.get("invoice_no")
            for row in case.evidence
            if row.active and row.kind == "invoice" and row.fields.get("invoice_no")
        ),
        None,
    )
    heading.caption(
        f"{display_title(case.title)} · Case {case.case_id}"
        + (f" · Invoice {invoice}" if invoice else "")
    )
    balance.metric("Open balance", fmt(case.open_balance))
    with total.container(key="invoice-total"):
        st.metric("Invoice total", fmt(case.invoice_total))

    review, documents, activity = st.tabs(
        ["Review", "Documents", "Activity"], key=f"case-tabs:{case.case_id}"
    )
    with review:
        render_actions(case, history, service)
        with st.expander("Decision and balance details"):
            st.text(f"Status: {case.status.value}")
            st.text(f"Insurance: {case.insurance.value}")
            st.text(f"Latest update: {case.status_reason or 'No update recorded.'}")
            _assessment(case)
        with st.expander("Insurance and dispute checklists"):
            st.caption(
                "Document readiness only. This is not a coverage or claim approval decision."
            )
            _readiness(case)
    with documents:
        _evidence(case, history, service)
    with activity:
        st.subheader("Activity")
        st.caption("Document changes, reviews, approvals, and MOCK receipts.")
        rows = timeline_rows(history)
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            st.info("No history recorded.")

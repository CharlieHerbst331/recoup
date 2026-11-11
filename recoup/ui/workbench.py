"""Authenticated single-workspace entry point; design/02 §4.5, §5.9 and §6."""

import hashlib
import hmac
import logging
import os
from threading import RLock
from time import monotonic

import streamlit as st

from recoup.app import RecoupConfig, build
from recoup.contracts.money import fmt


class AccessGate:
    """Process-wide serialization and failed-login throttle for one workspace."""

    def __init__(self):
        self.lock = RLock()
        self.retry_at = 0

    def login(self):
        candidate = st.session_state.pop("access_secret", "")
        expected = os.environ.get("RECOUP_ACCESS_SECRET", "")
        with self.lock:
            now = monotonic()
            if now < self.retry_at:
                return
            if valid_secret(expected) and hmac.compare_digest(
                candidate.encode(), expected.encode()
            ):
                st.session_state["access"] = (fingerprint(expected), now)
            else:
                # Global throttle survives new sessions; use a random 32+ character secret.
                self.retry_at = now + 2


def valid_secret(value):
    return len(value) >= 32 and value != os.environ.get("OPENAI_API_KEY")


def fingerprint(value):
    return hashlib.sha256(value.encode()).digest()


@st.cache_resource
def access_gate():
    return AccessGate()


def authenticated(gate):
    expected = os.environ.get("RECOUP_ACCESS_SECRET", "")
    if not valid_secret(expected):
        st.error("Access is unavailable. Ask the owner to configure the server access secret.")
        return False
    access = st.session_state.get("access")
    if access and hmac.compare_digest(access[0], fingerprint(expected)):
        if 0 <= monotonic() - access[1] < 8 * 60 * 60:
            return True
    st.session_state.pop("access", None)
    with st.form("login", clear_on_submit=True):
        st.text_input("Shared access secret", type="password", key="access_secret")
        st.form_submit_button("Sign in", on_click=gate.login)
    st.info("Sign in to use the shared workspace. Failed attempts are rate limited.")
    return False


def workbench(service):
    st.caption(f"SYNTHETIC DATA · MOCK actions · LLM: {service.llm.mode}")
    if st.button("Load SYNTHETIC demo cases (runs agent)"):
        service.load(["cases/demo/H", "cases/demo/C", "cases/demo/N"])
    cases = service.world.list_cases()
    if not cases:
        st.info("Load the demo cases to start.")
        return
    case_id = st.selectbox("Case", [case.case_id for case in cases])
    if st.button("Run agent"):
        service.run(case_id)
    view = service.world.view(case_id)
    st.caption(f"DEMO CLOCK: day {view.sim_day} ({view.sim_now.date()}, simulated)")
    st.subheader(view.title)
    st.write(f"Status: {view.status.value}; open balance: {fmt(view.open_balance)}")
    st.json(view.model_dump(mode="json"))
    for proposal in view.proposals:
        with st.expander(f"{proposal.kind.value} · version {proposal.version}"):
            st.write(proposal.draft_text)
            st.write(f"Recipient: {proposal.recipient}")
            if proposal.amount is not None:
                st.write(fmt(proposal.amount))
            st.json([citation.model_dump(mode="json") for citation in proposal.citations])
            key = f"{proposal.proposal_id}:{proposal.version}"
            if st.button(
                "Approve this version", key=f"approve:{key}", disabled=proposal.status != "proposed"
            ):
                service.approve(proposal.proposal_id, proposal.version)
                st.rerun()
            if st.button(
                "Submit MOCK action", key=f"submit:{key}", disabled=proposal.status != "approved"
            ):
                service.submit(proposal.proposal_id, proposal.version)
                st.rerun()


def main():
    st.title("Recoup shared workbench")
    gate = access_gate()
    if not authenticated(gate):
        return
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    # Keep SDK debug configuration and transport diagnostics out of hosting logs.
    for name in ("openai", "httpx", "httpcore", "httpx2", "httpcore2"):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
    with gate.lock:
        service = None
        try:
            config = RecoupConfig.from_env()
            service = build(config)
            workbench(service)
        except Exception:
            # Configuration/provider exceptions may contain secrets. Never render or log them.
            st.error(
                "The operation could not complete. Ask the owner to check server configuration."
            )
        finally:
            if service is not None:
                try:
                    service.world.close()
                finally:
                    client = getattr(service.llm, "client", None)
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            pass  # Transport cleanup must not expose provider diagnostics.


if __name__ == "__main__":
    main()

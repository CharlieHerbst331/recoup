"""Opaque identifiers; no business meaning is encoded in an identifier."""

from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def evidence_id(case_id: str, doc_ref: str, version: int) -> str:
    def component(value: str) -> str:
        return value.replace("%", "%25").replace("-", "%2D")

    return f"EV-{component(case_id)}-{component(doc_ref)}-v{version}"

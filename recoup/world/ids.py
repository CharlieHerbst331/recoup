"""Opaque identifiers; no business meaning is encoded in an identifier."""

from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"

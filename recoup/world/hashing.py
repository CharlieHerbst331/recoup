"""Deterministic hashes used by World (design/02 §3.6, §3.8)."""

import hashlib
import json


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(text: str, fields: dict) -> str:
    return digest(canonical({"text": text, "fields": fields}))


def basis_hash(members: list[str]) -> str:
    return digest("\n".join(sorted(members)))

"""Pure citation resolution (design/02 §3.7, §8.1)."""

from .interfaces import GateError
from .models import Citation, Evidence, FactRevision, FactSet, GateIssue, Scalar


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _render(value: Scalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def resolve_citation(
    c: Citation, basis: FactSet, evidence: list[Evidence], facts: list[FactRevision]
) -> Scalar | str | None:
    docs = {doc.evidence_id for doc in basis.docs}
    rows = {row.evidence_id: row for row in evidence if row.case_id == basis.case_id}
    revisions = {row.fact_id: row for row in facts if row.case_id == basis.case_id}
    members = {
        (fact.evidence_id, fact.key, fact.fact_id) for fact in basis.facts if fact.origin == "fact"
    }

    def fail(code: str, message: str) -> None:
        raise GateError([GateIssue(code=code, message=message)])

    def resolve(citation: Citation, visiting: frozenset[str]) -> Scalar | str | None:
        if citation.evidence_id not in docs:
            fail("superseded_citation", "Evidence is not active in the supplied basis")
        row = rows.get(citation.evidence_id)
        if row is None:
            fail("invalid_citation", "Evidence row is missing")
        locator = citation.locator
        quote = _normalize(citation.quote)
        if locator.startswith("fields."):
            key = locator.removeprefix("fields.")
            if key not in row.fields or quote != _normalize(_render(row.fields[key])):
                fail("invalid_citation", "Field or quote does not match")
            return row.fields[key]
        if locator == "text" or locator.startswith("page:"):
            text = row.text
            if locator.startswith("page:"):
                page = locator.removeprefix("page:")
                pages = text.split("\f")
                if not page.isdecimal() or not 1 <= int(page) <= len(pages):
                    fail("invalid_citation", "Page does not exist")
                text = pages[int(page) - 1]
            if quote not in _normalize(text):
                fail("invalid_citation", "Quote is absent from the cited text")
            return quote
        if locator.startswith("fact:"):
            fact_id = locator.removeprefix("fact:")
            revision = revisions.get(fact_id)
            if revision is None or revision.evidence_id != row.evidence_id:
                fail("invalid_citation", "Fact revision is missing or belongs to other evidence")
            if (row.evidence_id, revision.key, fact_id) not in members:
                fail("superseded_citation", "Fact revision is not in the supplied basis")
            if fact_id in visiting:
                fail("invalid_citation", "Cyclic fact citation")
            if quote != _normalize(_render(revision.value)):
                fail("invalid_citation", "Fact quote does not match")
            if revision.citation is None or revision.citation.evidence_id != row.evidence_id:
                fail("invalid_citation", "Fact has no citation against its evidence")
            resolve(revision.citation, visiting | {fact_id})
            return revision.value
        fail("invalid_citation", "Unknown locator")

    return resolve(c, frozenset())

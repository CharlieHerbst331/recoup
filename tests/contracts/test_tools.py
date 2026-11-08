import pytest

from recoup.contracts.tools import (
    BENCH_TOOLS,
    TOOL_DESCRIPTIONS,
    TOOL_REGISTRY,
    CheckPolicyResult,
    tool_json_schemas,
)


@pytest.mark.parametrize("include_bench", [False, True])
def test_tool_schema_registry_coverage(include_bench):
    expected = {**TOOL_REGISTRY, **BENCH_TOOLS} if include_bench else TOOL_REGISTRY
    schemas = tool_json_schemas(include_bench)
    assert len(schemas) == len(expected)
    assert [schema["name"] for schema in schemas] == list(expected)
    for schema in schemas:
        assert set(schema) == {"name", "description", "parameters"}
        assert schema["description"] == TOOL_DESCRIPTIONS[schema["name"]]
        assert schema["description"].endswith(".")
        assert schema["parameters"] == expected[schema["name"]][0].model_json_schema()
        assert "case_id" not in schema["parameters"].get("properties", {})
        assert expected[schema["name"]][1].model_json_schema()["type"] == "object"
    assert set(TOOL_DESCRIPTIONS) == set(TOOL_REGISTRY) | set(BENCH_TOOLS)
    schemas[0]["parameters"]["properties"].clear()
    assert tool_json_schemas()[0]["parameters"]["properties"]


def test_registry_names_and_bench_separation():
    assert set(TOOL_REGISTRY) == {
        "list_evidence",
        "read_evidence",
        "search_evidence",
        "get_ledger",
        "classify_line",
        "propose_fact",
        "run_rules",
        "check_policy",
        "readiness",
        "plan_missing_evidence",
        "fetch_from_system",
        "propose_decision",
        "draft_proposal",
        "schedule_followup",
        "request_approval",
        "end",
    }
    assert set(BENCH_TOOLS) == {"submit_approved", "wait_until"}
    assert not set(BENCH_TOOLS) & {s["name"] for s in tool_json_schemas()}


def test_policy_exclusion_citations_survive_round_trip():
    answers = CheckPolicyResult(
        answers=[
            {
                "question": "exclusions",
                "clause_key": f"exclusion.{i}",
                "applies": True,
                "value": f"clause-{i}",
                "computed_date": None,
                "basis": "proven",
                "note": "",
                "clause_citation": {
                    "evidence_id": "EV-H-policy-v1",
                    "locator": locator,
                    "quote": f"clause-{i}",
                },
            }
            for i, locator in [(1, "fields.exclusion.1"), (2, "fact:F-H-001")]
        ]
    )
    restored = CheckPolicyResult.model_validate_json(answers.model_dump_json())
    assert restored == answers
    assert restored.answers[0].clause_citation != restored.answers[1].clause_citation

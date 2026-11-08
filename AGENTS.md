# AGENTS.md (repo root, owned by Charles. Keep under 1 page)
Recoup is a single-user AR case workbench with an agent. Specs live in docs/design (01 functional, 02 technical) and docs/specs. The contract lives in recoup/contracts (PROPOSED v1; frozen at tag contract-v1 after F0).

Rules:
- Edit only the files your current task's handoff lists. Leave every other file alone.
- Never edit recoup/contracts/**, pyproject.toml, Makefile or this file unless you are Charles. Other people request contract changes in progress/<you>/CONTRACT_REQUEST.md and keep working against the current contract.
- Import the contract models. Never copy, redefine or fork them, not even temporarily. Respect the import DAG in docs/design/02 §2.
- Money is always integer cents (contracts.money.Money). Never use float for money. The model never computes amounts. Rules do.
- USD only. A non-USD bundle is quarantined at load (QuarantineRecord, no CaseView, no Money); see docs/design/02 §3.6.
- No real sends or network in tests. Tests use FakeLLM/ScriptedLLM, `SqliteWorld(":memory:")` (the only World) and fixtures; ui/bench tests go through `recoup.app.build`. Default runtime is RECOUP_LLM=fake.
- Every external action is a mock that needs a matching approval and produces a "MOCK-…" receipt.
- Drafts never affirmatively assert coverage, eligibility, payout, claim approval, recovery or a guarantee. Negated caveats and quoted policy text are fine. Label provenance everywhere: SYNTHETIC data, MOCK actions, LLM fake/replay/live.
- Don't add dependencies. Ask Charles.
- Before you say done, run `make check` (ruff + pytest), list every changed file, and append 3 lines to progress/<you>/PROGRESS.md (done / next / question).
- Normative definitions live only in docs/design/02 sections. Cite the section; never restate it in code or docs.
- Do one step per session, then stop.


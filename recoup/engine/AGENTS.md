# recoup/engine/AGENTS.md (owned by Sonny)
- You own recoup/engine/** and tests/engine/** only.
- The model chooses tools, classifies lines and proposes cited facts. Code computes money and dates and enforces the gates; the model never overrides a proven verdict. Never trust model amounts or citations without validating them (gates.py).
- Rules are pure functions keyed by reason and documents. Never branch on case_id.
- Policy facts come only from the case's insurance_policy document text and fields, quoted. Use no general insurance or legal knowledge.
- Before writing llm/openai_compat.py, read the current official OpenAI Python SDK tool-calling docs. Note the URL and date in progress/sonny/PROGRESS.md. Don't invent signatures.
- Ingestion never fabricates text. Unavailable OCR means status ocr_unavailable.

- Workflow r10: design/04 separates start-now unit work from real integration gates. Candidate 006-1 SHA is pinned there, not yet code-verified. Owned test doubles only; no copied shared types, no fake integration passes. Keep optional app imports in launch/integration paths, not import-time unit-test collection.

- USER-AUTHORIZED R10 TEST-LANE EXCEPTION: This downloaded handoff/design/04 supersedes only the candidate root AGENTS/docs instruction that ALL tests require SqliteWorld/app.build (and its design/02-only workflow-source restriction). Owner-local unit doubles are permitted; real providers remain mandatory for integration. All ownership, import, financial and safety rules remain unchanged. Only Charles may publish revised root/docs; Sonny/Carter use this external exception without editing those files.


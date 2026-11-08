# recoup/engine/AGENTS.md (owned by Sonny)
- You own recoup/engine/** and tests/engine/** only.
- The model chooses tools, classifies lines and proposes cited facts. Code computes money and dates and enforces the gates; the model never overrides a proven verdict. Never trust model amounts or citations without validating them (gates.py).
- Rules are pure functions keyed by reason and documents. Never branch on case_id.
- Policy facts come only from the case's insurance_policy document text and fields, quoted. Use no general insurance or legal knowledge.
- Before writing llm/openai_compat.py, read the current official OpenAI Python SDK tool-calling docs. Note the URL and date in progress/sonny/PROGRESS.md. Don't invent signatures.
- Ingestion never fabricates text. Unavailable OCR means status ocr_unavailable.


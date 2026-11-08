# Codex session template (paste first in every session, then the step prompt)
```
You are working in the Recoup repo (https://github.com/CharlieHerbst331/recoup) on branch [BRANCH]. You are the only agent in this session. Do the work yourself.
Read AGENTS.md and docs/INDEX.md first (before F0, read the bundle file named in your handoff instead). Design: docs/design/01-functional-design.md and 02-technical-design.md. Read only the sections this step names.
OWNERSHIP: you may create or edit only: [PATHS]. Do not edit anything else. If you need a contract change, write it in progress/[NAME]/CONTRACT_REQUEST.md and continue against the current contract.
STEP: [STEP PROMPT]
SELF-CHECK BEFORE DONE: 1) run `make check` and paste the tail; 2) for each acceptance item, name the test that proves it; 3) for a bug fix, show the test failing before and passing after; 4) list changed files and revert any outside OWNERSHIP; 5) append done/next/question to progress/[NAME]/PROGRESS.md. Then stop. Do not start the next step.
```


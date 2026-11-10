# UI refinement foundation — 2026-11-09 PT

## Scope and checkpoint

This session completes one preparation step: preserve the running build, make
the root README accurate and concise, and research design tools. It does not
implement the visual redesign. Current-session edits are limited to:

- `README.md`
- `progress/charles/UI-REFINEMENT-HANDOFF.md`
- `progress/charles/PROGRESS.md`

The existing UI and tests were committed unchanged as
`1b4b58f3474ab93da10ac555728d8c854cc36447` and pushed to `origin/charles/ui`.
The remote SHA was verified before creating `codex/enterprise-ui`.
Original untracked `arhcive/` and `recoup-006-charles-bundle-r10.md` inputs were
left in place, outside both commits. Local databases remain ignored.

The checkpoint preserves these 17 previously uncommitted files:

```text
progress/carter/PROGRESS.md
progress/charles/PROGRESS.md
recoup/ui/README.md
recoup/ui/__init__.py
recoup/ui/actions.py
recoup/ui/case.py
recoup/ui/case_page.py
recoup/ui/evidence.py
recoup/ui/queue.py
recoup/ui/streamlit_app.py
tests/ui/conftest.py
tests/ui/test_action_cards.py
tests/ui/test_case.py
tests/ui/test_demo_controls.py
tests/ui/test_evidence.py
tests/ui/test_queue.py
tests/ui/test_streamlit_app.py
```

## Findings and tools

Inspected the running queue and case H at localhost:8501, plus their source.
This is a Python/Streamlit frontend using `recoup.app.build`, with no React
application or JavaScript package manifest. The case page puts long evidence
tables ahead of the review actions; it exposes field names, business keys,
checklist IDs, and raw enums. The next pass needs clearer order and language as
well as consistent typography, spacing, and color.

| Tool | What it provides | Fit for Recoup |
| --- | --- | --- |
| [shadcn MCP](https://ui.shadcn.com/docs/mcp) and [official skill](https://ui.shadcn.com/docs/skills) | Component registry search, installation, and composition guidance | Strong candidate for a future React frontend. Its [supported setup](https://ui.shadcn.com/docs/installation) does not directly target this Streamlit app. |
| [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | Guidance on visual direction, typography, layout, and critique | Useful design guidance; it is not a component library or a Streamlit adapter. Discoverable through [skills.sh](https://skills.sh/anthropics/skills/frontend-design). |
| [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Design catalogs, theme and interaction guidance, and assistant integrations | An alternative skill source. Streamlit is not listed among its stack-specific guides. |
| Product Design plugin | Flow audits, visual directions, and interactive prototypes | Installed after the preparation checkpoint. Used for the screenshot audit and three visual concepts below. |

Recommendation: improve the existing Streamlit workbench first using native
layout and [theme controls](https://docs.streamlit.io/develop/concepts/configuration/theming).
Use a design skill to guide deliberate choices and browser review to judge the
result. Reserve shadcn MCP and its skill for a separately scoped frontend
migration. No skills, MCP servers, packages, or runtime dependencies were installed.

## Proposed next implementation step

Create a calm finance workspace with a neutral canvas, a restrained blue action
color, readable type, and consistent spacing. Lead the queue with customer,
case subject, open balance, next deadline, and a clear route into review.
Lead each case with its summary and proposed actions; group documents,
checklists, and history into focused sections. Show readable document titles
beside citations, with technical identifiers available in expanded details.

Copy examples: “Quarantined bundles” → “Imports needing attention”; “Inject
document” → “Add supporting document”; “Line decisions” → “Deduction review”;
“Status reason” → “Latest update”. Keep demo controls in a secondary area.
UI behavior and provenance requirements remain defined by design/02 §6;
approval and staleness behavior remain defined by §4.2–4.3.

Proposed file scope for that next session: `.streamlit/config.toml`,
`recoup/ui/{streamlit_app.py,queue.py,case_page.py,case.py,actions.py,evidence.py,README.md}`,
`tests/ui/{test_streamlit_app.py,test_demo_controls.py,test_queue.py,test_case.py,test_action_cards.py,test_evidence.py}`,
and `progress/charles/{UI-REFINEMENT-HANDOFF.md,PROGRESS.md}`.
Verify queue → case → edit → approve → MOCK submit → next due, plus stale
actions, empty/import-error states, keyboard use, and desktop/narrow layouts.
Use `make check` and browser screenshots. No backend or contract changes are
part of this proposed step.

## Verification

`make check`: Ruff lint and formatting passed; 1,123 tests passed and 2 optional
OCR tests skipped in 330.64 seconds. The suite ran against the saved build;
all subsequent edits are documentation only. README local links resolve, and
`git diff --check` passes. The README is 330 words, down from 422, with stale
branch status and provider internals replaced by current run instructions.

## Product Design follow-up — visual selection pending

The user installed Product Design. Followed its index, audit, context, and
ideation workflows against the existing app; no saved product context existed.
This step produces visual choices before implementation.

Fresh audit evidence is saved outside the source tree at
`/Users/charlieherbst/.codex/generated_images/recoup-design-audit-2026-11-09/`.
Each screenshot was captured in the in-app browser, saved, reopened, and reviewed:

1. `01-case-queue.png` — Functional queue; letter-only case selection separates
   navigation from the meaningful customer/subject/balance shown in the table.
2. `02-case-overview.png` — Functional detail navigation; oversized header and
   status banners fill the first screen before the balance and proposed actions.
3. `03-action-review.png` — Separate approval/submission controls are visible,
   but raw business keys, target enums, and cents allocations hinder review.

Accessibility limits: desktop screenshot/structure review only. Keyboard flows,
focus, screen-reader output, measured contrast, zoom, and narrow-screen reflow
have not been verified. No edits, approvals, submissions, or clock advances were
performed during browser inspection.

Three image-only concepts were generated with the built-in Image Gen tool, each
receiving all three accepted screenshots. Display order is authoritative:

| Displayed option | Direction | Local generated image |
| --- | --- | --- |
| 1 | Review Desk: case summary, deduction table, action column | `/Users/charlieherbst/.codex/generated_images/01a1c458-1d0d-7c83-a372-848a9c0f6abe/exec-8f296ab8-e173-4ba5-8d75-976ffbadc0b1.png` |
| 2 | Case Navigator: readable case list beside focused draft review | `/Users/charlieherbst/.codex/generated_images/01a1c458-1d0d-7c83-a372-848a9c0f6abe/exec-f8e7bd75-4604-4ee0-b174-a28cbc18cf93.png` |
| 3 | Evidence Review: deduction and supporting document side by side | `/Users/charlieherbst/.codex/generated_images/01a1c458-1d0d-7c83-a372-848a9c0f6abe/exec-cfd12714-a5fc-45fa-b645-7c2a3b460fae.png` |

All are design references, not functioning builds. At implementation, read
amounts, target labels, recipients, and action state from existing contract
models. In particular, option 1's dispute recipient is misrendered as MOCK ERP;
use the actual buyer portal target. In option 2, label unsent line responses
“Proposed dispute” instead of implying they have been submitted. No generated
source content or state should replace the stored case data.

The ideation skill explicitly requires selection before build work. Await the
user's choice, then use that displayed image as the visual target, preserve the
existing Streamlit/application architecture, and follow the proposed file scope
above. No frontend code, dependencies, or backend files changed in this step.

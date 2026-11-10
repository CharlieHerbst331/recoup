# UI refinement — current handoff, 2026-11-10 PT

## Result and scope

Implemented the user's selected **option 2 / Case Navigator**, with the requested
Ramp-inspired neutral palette, black primary buttons, pale lime selection, and
modest corner radii. The existing Streamlit app, SQLite persistence, and app
facade remain the runtime. No dependencies, backend, contracts, or real actions
were added. Normative UI and action behavior: design/02 §6 and §4.2–4.3.

The previous build is preserved on `origin/charles/ui` at
`1b4b58f3474ab93da10ac555728d8c854cc36447`. This implementation is on
`codex/enterprise-ui`; main is unchanged. Prior research, audit, and the original
three-option mapping are preserved in this file's history at `6af3311`.

Current task's changed files (complete list):

- `.streamlit/config.toml`
- `recoup/ui/README.md`
- `recoup/ui/actions.py`
- `recoup/ui/case_page.py`
- `recoup/ui/queue.py`
- `recoup/ui/streamlit_app.py`
- `tests/ui/test_action_cards.py`
- `tests/ui/test_demo_controls.py`
- `tests/ui/test_evidence.py`
- `tests/ui/test_streamlit_app.py`
- `progress/charles/UI-REFINEMENT-HANDOFF.md`
- `progress/charles/PROGRESS.md`

## Behavior

The case list uses customer names, subjects, and formatted balances. Review,
Documents, and Activity tabs organize each case. The main review shows the
current proposed action, recipient target, allocations in USD, draft, edit form,
and separate approval/submission controls. Technical identifiers, earlier
versions, supporting details, rejection, and additional actions remain available
in expandable sections. A case-level MOCK receipt stays visible when the next
pending action becomes the main review.

The existing SYNTHETIC/MOCK/LLM/simulated-clock labels remain visible in a compact
banner. Money is formatted from imported contract values; no new financial
calculations were added. The UI instructions describe the new labels and tabs.

## Visual sources and evidence

Selected original option 2:
`/Users/charlieherbst/.codex/generated_images/01a1c458-1d0d-7c83-a372-848a9c0f6abe/exec-f8e7bd75-4604-4ee0-b174-a28cbc18cf93.png`.
The requested Ramp variation was generated and shown before implementation:
`/Users/charlieherbst/.codex/generated_images/01a1c458-1d0d-7c83-a372-848a9c0f6abe/exec-cd6020e3-cc6a-47b5-bc72-b38690eb6833.png`.
Ramp's current colors and buttons were inspected at https://ramp.com/.

Evidence folder:
`/Users/charlieherbst/.codex/generated_images/recoup-ramp-implementation/`.
Important files: `ramp-reference.png`, `comparison-first.png`,
`comparison-final.png`, `comparison-review-detail.png`,
`implementation-desktop-final.png`, `mobile-review-top.png`,
`mobile-review-controls.png`, `mobile-case-navigation.png`,
`desktop-sidebar-collapsed.png`, `documents.png`, `empty-state.png`,
`mock-receipt-confirmation.png`, and `day-3-correction.png`.

## Design QA

QA is recorded here to respect this handoff's repository file scope; a standalone
`design-qa.md` is also saved in the evidence folder outside the source tree.

State: case H, day 0, unapproved dispute, Review tab, sidebar expanded. Source
and final implementation are both **1487 × 1058** pixels, CSS viewport
1487 × 1058, devicePixelRatio 1; no density normalization or resizing in the final
comparison. Source and implementation were inspected together in the full-view
and focused review-region comparison files. Additional viewport: 390 × 844.
The temporary browser viewport override was reset after verification.

Earlier findings and fixes:

1. **P2 — Excessive vertical space and weak case navigation.** The first capture
   placed review controls too low and used a radio-style presentation without
   clear customer hierarchy. Reduced header gaps, moved queue navigation into
   the sidebar, styled the native case rows, and moved editing into the draft.
2. **P2 — Narrow-screen toolbar overlap.** Reserved mobile toolbar space and
   gave its fixed header a solid background. Post-fix mobile captures show
   readable provenance and usable full-width approval controls.
3. **P2 — Collapsed desktop sidebar retained empty space.** Limited custom width
   constraints to expanded sidebars. Verified collapsed sidebar width 0, main
   workspace width 1487, and no page-wide overflow.

Final fidelity review:

- **Typography:** neutral Arial/system sans, clear customer/action headings,
  compact native table type, readable labels, and preserved long-draft wrapping.
- **Spacing/layout:** case list, case summary, three tabs, and focused draft
  review retain option 2's structure. Native widgets are deliberately more
  compact than the illustrative mock. Secondary details remain accessible.
- **Colors/tokens:** white/light neutral surfaces, near-black primary controls,
  pale lime case/status accents, restrained borders, and six-pixel button radii.
- **Images/icons:** the target needs no raster imagery. Text wordmark and native
  Streamlit widget icons are used; no placeholder artwork or custom SVG assets.
- **Copy/data:** actual contract-backed values and recipients replace conceptual
  mock content; line responses say Proposed dispute before submission. Extra
  mock date chrome was omitted. The $1,800 credit remains separate from dispute.
- **Interactions:** arrow-key case navigation, tabs, document expansion, edit,
  approve, MOCK submit, receipt confirmation, and next-due refresh were exercised.

No actionable P0/P1/P2 findings remain. P3 follow-up: some document titles already
contain a version suffix, so their expanded-list labels can repeat the version.
A full screen-reader/zoom/accessibility certification was not performed. Native
wide data tables scroll within their component on narrow screens; the document
itself has no horizontal overflow.

Browser error logs contained expected health-check disconnects during deliberate
preview-server restarts, last at 08:20:06 UTC. No new application errors were
reported during the final walkthrough after the server started at 08:20:08 UTC.

**final result: passed**

## Verification and delivery

Final `make check`: Ruff lint/format PASS; **1124 passed, 2 optional OCR tests
skipped in 396.23 seconds**. Existing integration/gate coverage remains in place;
added a case-navigation/tab regression proving navigation does not mutate cases.
Two focused edit/approve/submit and action-rendering tests also passed.
`git diff --check` passes.

Browser walkthrough used `runs/ui-polish-review.db`: revised the dispute draft,
approved that exact version, separately submitted it to obtain `MOCK-DISP-0001`,
and advanced to day 3. The refreshed correction and original receipt were both
visible. The delivered preview uses a separate fresh `runs/ui-polish-preview.db`
with H/C/N at day 0, so the user can inspect an untouched review flow.

Preview: http://localhost:8502. Existing original demo data was left unchanged.
Runtime databases and screenshots remain outside tracked source. Original
untracked `arhcive/` and `recoup-006-charles-bundle-r10.md` inputs are untouched.
Stop after this implementation step; no merge or deployment is part of it.

# Charles final demo acceptance — 2026-11-09

Reviewed integrated engine commit `e12fef4` against functional design §10 and
technical design §9–10. This is offline application integration evidence; it is
not independent Reviewer/Verifier sign-off, live-model acceptance, or a contract
freeze.

The existing `tests/engine/test_007_8_integration.py::test_full_offline_h_c_n_demo`
already covers the published demo timeline using direct World approvals/submits.
The new `tests/app/test_final_integration.py` adds the missing public-facade path:
all load, edit, approve, submit, replay and advance operations go through `Recoup`.
Every test uses `build(RecoupConfig(db=":memory:", llm="fake"))` with the actual
engine and the app suite's network-blocking fixture. All inputs are SYNTHETIC;
all external receipts are MOCK. No keys, sends, provider calls, or dependencies
were used.

Observed acceptance assertions:

- H day 0: credit receipt 180000 cents reduces balance from 624000 to 444000;
  edited dispute version binds approval and issues a 444000-cent MOCK receipt.
- H day 3: published POD v2 plus inspection produce a 312000-cent correction
  referencing the original receipt and a D1-only incremental credit for 312000.
  Balance reaches 132000. The original D2 credit is not reposted.
- Replaying the original dispute submit after the evidence change returns its
  immutable old receipt without changing the ledger or adding a receipt.
- H's unsent variant voids the original approved dispute at day 3, rejects its
  old submit, and replaces it with a D2-only 132000-cent dispute without a
  correction or an additional receipt.
- H day 17 follow-up and day 35 notice submit successfully; notice basis is
  132000 cents. Day 95 claim has collection history and completed waiting period,
  but missing statement and restricted disputed portion. Approval alone cannot
  bypass submission readiness: `claim_not_ready` blocks the mock action.
- C submits only its supported credit and reaches zero; N submits only an
  information request and retains 215000 cents. Both submit replays are no-ops.
- The published counteroffer fixture is selected by the actual fake harness;
  its 10000-cent offer selector `A/B` survives approval/receipt and repeated
  submission without changing the ledger.
- The published multi-invoice remittance through the actual default-engine facade
  conserves its 23000 cents across allocations plus unapplied cash, reaches
  balances 0 and 5000, and replay preserves all three cases' ledgers.

Normative behavior remains in technical design §3.9, §4.5, and §5.4–5.7; the
values above describe fixture execution rather than introducing new rules.

Verification:

```text
ruff check tests/app/test_final_integration.py: PASS
ruff format --check tests/app/test_final_integration.py: PASS
pytest tests/app/test_final_integration.py -q -x: 4 passed in 66.59s
pytest tests/app/test_final_integration.py -k unsent -q: 1 passed, 4 deselected in 8.07s
```

The second pytest invocation verifies the fifth case added after the initial
four-case run. The parent integration task runs the required final `make check`
after these changes; its aggregate acceptance records that result.

Changed files for this verification task:

- `tests/app/test_final_integration.py`
- `progress/charles/006-FINAL-DEMO-ACCEPTANCE.md`

Remaining external gates are owned Reviewer/Verifier acceptance, any required
contract freeze/merge authorization, live or recorded evaluation, and optional
OCR availability. Offline success does not claim any of those gates.

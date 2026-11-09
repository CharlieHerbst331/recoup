# SYNTHETIC financial integration examples

These examples exercise design/02 §3.9 and §5.4. They contain no real customer data.

Run `recoup --db /tmp/recoup-remittance-demo.db load-remittance cases/ambition/multi-invoice/remittance.json`.
The executable app/CLI tests verify the resulting balances, explicit unapplied cash,
restart audit and replay behavior. Use a fresh database for a new demonstration.

Load `cases/ambition/counteroffer` using the ordinary `load` command. The existing
engine produces a proven disputed D2 and the World exposes resolving cited offer
facts. Sonny's engine counteroffer derivation/tool/gate implementation remains the
next owner task; the fixture does not claim that path is already implemented.
`tests/app/test_financial_intake.py` verifies the shared prerequisites, while
`tests/world/test_counteroffer_boundary.py` checks the World defenses independently.

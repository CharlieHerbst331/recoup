# SYNTHETIC financial integration examples

These examples exercise design/02 §3.9 and §5.4. They contain no real customer data.

Run `recoup --db /tmp/recoup-remittance-demo.db load-remittance cases/ambition/multi-invoice/remittance.json`.
The executable app/CLI tests verify the resulting balances, explicit unapplied cash,
restart audit and replay behavior. Use a fresh database for a new demonstration.

Load `cases/ambition/counteroffer` using the ordinary `load` command. The existing
engine produces a proven disputed D2 and drafts a cited conditional counteroffer.
Inspect its proposal ID and version with `status COUNTEROFFER`, then review,
approve and submit it through the usual mock-action commands. Sonny's published
engine implements the derivation, tool and gate path. The app/engine acceptance
checks exercise the real fixture and approval-bound MOCK receipt; World tests
check the persistence defenses independently. See Charles's final integration
report for the current verification scope and limitations.

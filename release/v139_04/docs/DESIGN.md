# V139.04 Recovery Validation Design

Validates the complete V139.03 unlock evidence before an autonomous cycle may resume.

Required after `NEXT_CYCLE_UNLOCKED`:

- Unlock result is PASS and next-cycle ready.
- Unlock token identity matches result.
- Exactly one matching unlock ledger event exists.
- Recovery snapshot identity and verification flags match.
- No source safe mode is active.

Before unlock exists, the expected result is `WAIT_UNLOCK`.

No credentials, broker network, or order submission is used.

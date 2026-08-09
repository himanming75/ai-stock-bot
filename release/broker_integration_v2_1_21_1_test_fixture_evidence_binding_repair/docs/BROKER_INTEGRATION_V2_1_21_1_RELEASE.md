# V2.1.21.1 — Test Fixture Evidence Binding Repair

Base HEAD remains `a7895093` because V2.1.21 failed before commit/push.

## Root cause

The V2.1.21 production validator intentionally requires the latest V2.1.17
qualification `evidence_key` to match the current V2.1.15 observation
`snapshot_fingerprint`.

The original synthetic READY fixture wrote a READY qualification without an
`evidence_key`, so the production safety binding correctly returned NOT_READY.

## Repair

Only the V2.1.21 test fixture is corrected.

The fixture now:
- writes a current V2.1.15 `latest_snapshot.json`
- sets a deterministic `snapshot_fingerprint`
- writes the same value as V2.1.17 `evidence_key`
- validates that the READY path succeeds only when both identifiers match

No production safety requirement is weakened.

## Safety

- E*TRADE OAuth remains disabled
- Sandbox Preview/Place remain disabled
- Broker orders remain zero
- PROD remains locked
- Live trading remains locked

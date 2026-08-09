# Broker Integration V2.1.19.1 — Canonical Paper Gate Semantic Correction & Audit

Base commit: `78e7886a`

## Why this correction exists

V2.1.17 incorrectly labeled the generic E*TRADE bridge confidence floor `0.60` as the canonical Paper gate.

Repository semantics are distinct:

- Generic E*TRADE bridge confidence floor: `0.60`
- Canonical Paper candidate confidence floor: `0.75`
- Canonical Paper minimum reward/risk: `1.0`

These gates are not semantically equivalent.

## Corrections

### V2.1.17 qualification

Corrected to require:

- confidence >= 0.75
- reward/risk >= 1.0
- reward/risk evidence must be present
- corrected semantic marker: `CORRECTED_V2_1_19_1`

Missing reward/risk now blocks readiness.

### V2.1.18 packet builder

Legacy `0.60` READY rows are no longer accepted.

Only corrected qualification rows can create a review packet.

### V2.1.19 approval guard

Legacy review packets cannot be approved.

Approval validation also revalidates the corrected semantic contract.

## Legacy runtime audit

No runtime data is deleted.

The audit reports legacy qualification, review packet index, and approval rows.

Corrected code blocks legacy artifacts from progressing downstream.

## Safety

- automatic Sandbox execution remains disabled
- E*TRADE OAuth remains disabled
- Sandbox Preview remains disabled
- Sandbox Place remains disabled
- broker orders remain zero
- PROD remains locked
- live trading remains locked

## Important next dependency

Current V2.1.16 evidence may not contain reward/risk.

Such evidence must remain NOT_READY until an upstream canonical reward/risk provenance bridge is implemented and validated.

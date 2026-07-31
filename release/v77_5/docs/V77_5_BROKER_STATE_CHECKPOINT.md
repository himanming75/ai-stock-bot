# V77.5 Broker State Checkpoint

## Purpose
Serialize a reconciled offline broker state into a tamper-evident checkpoint.

## Source anchors
- V77.4 reconciliation SHA256: `7582d94ae2b2f9155bca69d7bbaebb8f081dd362f7aabc5d5a6016db4948b3cc`
- V77.4 verification SHA256: `06a1b2b6f3c8c271464f1f7ebfe7776d4432126f5471ee216a26c8c8c51039a9`
- Framework commit before installation: `7e21abb`

## Captured state
- starting cash, current cash, buying power, equity
- positions
- orders
- fills
- lifecycle events
- source reconciliation status and issue count

## Integrity controls
- canonical JSON serialization
- SHA-256 state seal
- required-field validation
- round-trip read/write verification
- cash tamper detection
- missing-section detection
- unreconciled-state checkpoint rejection

## Safety
- offline only
- network disabled
- broker disconnected
- actual broker submissions remain zero
- live trading remains unauthorized

## Next phase
`V77.6 Restart Recovery Replay`

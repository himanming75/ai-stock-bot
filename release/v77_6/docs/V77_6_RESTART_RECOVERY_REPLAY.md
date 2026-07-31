# V77.6 Restart Recovery Replay

## Purpose
Restore a fresh offline simulator from a verified V77.5 checkpoint and prove
that the recovered state reproduces the checkpoint exactly.

## Source anchors
- V77.5 checkpoint framework SHA256: `d9a5804f52f6b8b5b66fa190ddea7af91e16b14187c9989d386b928bb046d3d4`
- V77.5 sample state SHA256: `03baec3f972138369629a5038afb79c5018e4095f5602cc24bcbadc71ef044f0`
- V77.5 verification SHA256: `a41216d0f66662e3f16edce669159d9e98c81bd97aa25fbafe18cf1e21823e6d`
- Framework commit before installation: `01e6612`

## Restored state
- cash
- positions
- orders and client-order mapping
- fills
- events
- order sequence
- fill sequence
- event sequence

## Replay verification
- post-restore reconciliation
- regenerated checkpoint SHA256 equality
- cash, position, order, fill, and event equality
- order ID continuity
- fill ID continuity
- event sequence continuity

## Safety
- offline only
- network disabled
- broker disconnected
- actual broker submissions remain zero
- live trading remains unauthorized

## Next phase
`V77.7 Recovery Continuation Safety`

# V83.32A Verify Wait-Trigger Hotfix

This hotfix changes only the V83.29-V83.32 verifier.

Accepted safe outcomes:

- Normal `PASS`
- `LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER`
- `LOCAL_TRIGGER_DISPATCH_DRY_RUN_READY`
- `LOCAL_TRIGGER_DISPATCH_SAFE_MODE` when the only issue is an absent trigger plan or inactive trigger lock

Still rejected:

- Disallowed action, script, or arguments
- Duplicate dispatch
- Timeout or nonzero return code
- Safety policy violations
- Broker, order, network, or live-trading activity

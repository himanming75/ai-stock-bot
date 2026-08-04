# V221-V225 Paper Operations Automation V2

Workflow:

1. Pre-market policy check
2. Signal collection
3. Risk Engine V2 gate
4. Paper order plan
5. Idempotency registration
6. Submission policy gate
7. Fill-monitor state
8. Position reconciliation
9. Daily operations report
10. Final checkpoint and recovery plan

Default safety:

- Real network: disabled
- Paper submission: disabled
- Live submission: disabled
- Broker write: disabled
- Actual Live orders: zero

V225 provides the automation state machine and safety foundation. It intentionally does not include a broker submission client.

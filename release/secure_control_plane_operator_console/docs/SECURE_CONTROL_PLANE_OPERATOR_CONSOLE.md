# Secure Control Plane and Operator Console

This package provides an offline, read-only operator control layer:

- operator roles and permissions;
- expiring session previews;
- two-step confirmation challenges;
- configuration, strategy, runtime, worker, scheduler, kill-switch, and
  emergency-stop request previews;
- separate approver review;
- policy enforcement;
- self-approval rejection;
- idempotency protection;
- sensitive-value redaction;
- control-plane audit ledger;
- local read-only web console.

No request is applied. The console rejects POST requests. No runtime, strategy,
configuration, worker, scheduler, kill-switch, emergency-stop, network, broker,
or order action occurs.

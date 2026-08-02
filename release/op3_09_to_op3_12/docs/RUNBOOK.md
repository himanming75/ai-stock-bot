# Paper Order Lifecycle Runbook

1. Run local tests using copied snapshots.
2. Confirm the prior OP3.05-OP3.08 result contains one successful Paper order.
3. For actual status, configure Paper credentials and use `-EnableNetwork`.
4. Review order status, fill report, reconciliation report, and recovery token.
5. Re-run read-only monitoring until the order reaches a terminal state.

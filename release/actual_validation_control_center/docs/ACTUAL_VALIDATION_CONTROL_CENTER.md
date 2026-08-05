# Actual Validation Control Center

This bundle consolidates the already implemented P2, P3, P4, and P5 Actual
validation states.

It provides:

- combined Actual validation status;
- market-day environment preflight;
- wrapper sequence for validating an explicitly submitted Paper order;
- P4 and P5 next-action routing;
- fail-closed Paper completion certificate;
- Live Actual sequence report.

The installer never uses broker network access and never submits an order.
The market-day sequence does not create the first Paper order. It requires the
Client Order ID of a Paper order that the operator explicitly submitted.

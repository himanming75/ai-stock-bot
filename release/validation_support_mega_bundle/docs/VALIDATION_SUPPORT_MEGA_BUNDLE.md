# Validation Support & Automation Mega Bundle

This package supports P2 and P3 without performing them.

Included:

- P2/P3 preflight;
- API error classification;
- retry/backoff planning;
- rate-limit detection;
- account, position, order, and clock schema validation;
- credential metadata health checks;
- validation report and failure summary;
- Git and release-file audit;
- incident reproduction snapshots.

Retry logic is planning-only. It never automatically repeats a network call.

Incident snapshots include validation results and configuration-safe metadata,
but never include encrypted credential payloads or plaintext credentials.

No broker read, broker write, order submission, cancellation, portfolio change,
or external network call occurs.

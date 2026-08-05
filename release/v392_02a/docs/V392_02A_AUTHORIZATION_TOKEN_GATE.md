# V392.02A Authorization Token Gate

## Purpose

Convert an approved V392.01A authorization into a cryptographically signed,
short-lived, single-use token.

## Security controls

- HMAC-SHA256 signature;
- Proposal ID binding;
- Proposal hash binding;
- Policy hash binding;
- Symbol and side binding;
- Paper-only environment;
- expiration validation;
- issued-at validation;
- one-time consumption;
- replay detection.

## Boundary

An accepted token only allows dispatch-gate preparation. Broker write and all
Paper/Live submission remain disabled.

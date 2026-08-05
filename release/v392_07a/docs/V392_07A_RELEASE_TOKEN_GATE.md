# V392.07A Release Token Gate

## Purpose

Convert an approved V392.06A Queue Release Authorization into a signed,
short-lived, single-use Release Token.

## Security controls

- HMAC-SHA256 signature;
- Release ID binding;
- Dispatch ID binding;
- Token ID binding;
- Proposal ID binding;
- Queue hash binding;
- FIFO Head Entry hash binding;
- five-minute TTL;
- single-use enforcement;
- replay detection;
- Paper-only environment.

## Boundary

An accepted Release Token only allows evaluation by the next local dispatch
release gate. Queue mutation, dispatch execution, broker writes, and Paper/Live
submission remain disabled.

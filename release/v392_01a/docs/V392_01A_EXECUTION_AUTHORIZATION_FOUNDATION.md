# V392.01A Execution Authorization Foundation

## Purpose

Create a second fail-closed gate after the V391 Risk Governor.

A Risk Governor `ALLOW` decision does not authorize an order by itself. This
stage additionally verifies:

- V391.10A result and `ALLOW` decision;
- proposal identifier;
- canonical proposal SHA-256 hash;
- Risk Policy hash;
- exact manual approval phrase;
- approving operator and reason;
- unexpired approval;
- Paper target only;
- automatic authorization disabled.

## Approval phrase

`APPROVE_PAPER_EXECUTION_AUTHORIZATION`

## Boundary

Approval in this stage only permits dispatch preparation in the next stage.
Broker write and Paper/Live submission remain disabled.

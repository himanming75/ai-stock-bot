# OP3.05-OP3.08 Single Controlled Paper Order Execution

- OP3.05 Validate a single prepared Paper order and create a preview
- OP3.06 Submit exactly one order to Alpaca Paper only after explicit gates
- OP3.07 Record the Paper submission in an append-only ledger
- OP3.08 Write the execution token

Default execution is local preview only. Actual Paper submission requires:
`-EnableNetwork`, `-EnableSubmission`, configured Paper credentials, and the
exact submission approval phrase.

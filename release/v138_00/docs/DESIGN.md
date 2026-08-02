# V137.01–V138.00 Final Paper Submission Approval Gate

This stage validates the complete V137 preview package and optionally creates one local final-approval token.

Requirements:

- preview state READY_FOR_SUBMISSION_APPROVAL
- order preview present
- risk snapshot approved
- exposure snapshot approved
- preview approval gate present
- preview gate still has actual_submission_allowed=false
- deterministic preview/cycle/client-order identities
- exact human approval phrase

The exact phrase is:

`APPROVE EXACTLY ONE CONTROLLED ALPACA PAPER ORDER`

Even after local approval, this stage performs no broker network request and submits no order.

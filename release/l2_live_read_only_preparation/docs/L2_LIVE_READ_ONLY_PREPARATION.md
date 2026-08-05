# L2 Live Read-Only Preparation

L2 prepares GET-only Live broker models for:

- account;
- positions;
- open orders;
- market clock;
- asset tradability.

The offline qualification uses fixtures only. Actual Live API access remains
blocked until P5 Actual Paper completion, L1 safety approval, active Live Kill
Switch review, and explicit operator-controlled L2 qualification.

POST, PATCH, PUT, and DELETE are rejected by the GET-only guard.

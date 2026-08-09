# Broker Integration V2.1.1 — Sandbox Preview Diagnostic Repair

Base commit: `9f43b434`

## Root cause of the observed failure
OAuth completed successfully. The failure occurred on the Sandbox Preview Order POST and E*TRADE returned HTTP 400.

The V2.1 transport used urllib without reading the HTTPError response body, so the actual E*TRADE error code/message was hidden.

## Repair
- Preserve and print E*TRADE HTTP error response body.
- Fetch Sandbox account list using the same current OAuth access token.
- Select the account by number instead of manually copying accountIdKey.
- Do not display accountIdKey.
- Show non-sensitive order diagnostic fields.
- If Preview fails, Place is never sent.

## Safety
- Sandbox only.
- Real securities/money: none.
- Production order submission remains locked.
- Credentials and OAuth token values are not printed.

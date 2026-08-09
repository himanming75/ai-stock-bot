# Broker Integration V2 — E*TRADE Read-only OAuth

Base commit: `cb068d8c`

## Non-duplication

V2 does not create another broker framework.

It extends the existing `broker_integration_v1` package and reuses:
- `broker.contracts_v77_1` as the canonical broker contract
- the existing Broker Integration V1 bridge
- the existing `ETradeReadOnlyAdapter`
- the existing E*TRADE normalization layer
- the existing Alpaca stack

V2 adds only the missing OAuth/network boundary for E*TRADE read-only access.

## OAuth

E*TRADE's retail Developer Platform uses OAuth 1.0a and HMAC-SHA1.

Implemented:
- OAuth HMAC-SHA1 signer
- official E*TRADE signature test vector
- request-token flow
- authorization URL generation
- verification-code exchange for access token
- renew and revoke calls
- explicit network opt-in
- read-only GET whitelist

## Credential handling

V2 deliberately does not create another credential vault.

Consumer key/secret are read only from the current process environment:
- `ETRADE_CONSUMER_KEY`
- `ETRADE_CONSUMER_SECRET`

Request/access token values are held in process memory only.
They are not printed and are not persisted.

Only a redacted account snapshot may be written under:
`runtime/etrade_readonly_v2/`

The repository already ignores `runtime/`.

## Build behavior

Normal V2 installation performs no E*TRADE network access.

Without credentials:
`WAITING_FOR_CREDENTIALS`

With credentials but before explicit OAuth execution:
`READY_FOR_USER_AUTHORIZED_READONLY_CONNECTION`

Actual OAuth/network access is a separate explicit command:
`START_ETRADE_READONLY_OAUTH_V2.ps1`

## Safety

Always locked in V2:
- order submission
- order cancellation
- order replacement
- Live trading

The OAuth read-only transport permits only GET account endpoints.

## E*TRADE token lifecycle

According to E*TRADE documentation:
- access tokens can become inactive after two hours without API activity
- Renew Access Token can reactivate an inactive token
- tokens normally expire at midnight US Eastern time
- Revoke Access Token is recommended when finished

## Licensing

E*TRADE's current API terms describe the V1 API code as a non-commercial license for internal proprietary tools managing one's own E*TRADE account. Commercial/SaaS use should be handled separately with the appropriate E*TRADE vendor/commercial arrangements.

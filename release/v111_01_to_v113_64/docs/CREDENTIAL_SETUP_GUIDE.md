# V111-V113 Credential Setup Guide

This stage does not load or use credentials.

It only defines the environment-variable names that later stages may use:

## Alpaca

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

## Interactive Brokers

- `IBKR_USERNAME`
- `IBKR_ACCOUNT_ID`

## E*TRADE

- `ETRADE_CONSUMER_KEY`
- `ETRADE_CONSUMER_SECRET`
- `ETRADE_ACCESS_TOKEN`

Do not place secret values in Git, JSON policy files, screenshots or chat messages.

The default selected adapter is `MOCK_READ_ONLY`. Real network access remains disabled.

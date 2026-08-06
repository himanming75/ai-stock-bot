# E*TRADE Sandbox OAuth and Read-Only Guide

1. Install and run the offline tests.
2. Run `RUN_ETRADE_SANDBOX_OAUTH_WIZARD.ps1`.
3. Enter the Sandbox Consumer Key and Secret. Input is hidden.
4. Approve access in the browser and paste the verification code.
5. Run `RUN_ETRADE_SANDBOX_READ_ONLY_VALIDATION.ps1`.

Credentials are encrypted with Windows DPAPI at:

`runtime/secrets/etrade_sandbox.dpapi.json`

Never commit that file or share its contents.

Only account list, balance, portfolio, order history, and quote reads are
implemented. Order preview, place, modify, and cancel remain disabled.

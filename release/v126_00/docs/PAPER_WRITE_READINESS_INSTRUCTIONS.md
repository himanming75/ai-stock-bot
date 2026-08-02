# Paper Write Readiness Certification

First run the default gate. It should produce `READ_ONLY_READY`.

To issue a Paper write readiness certificate without submitting an order:

```powershell
$env:AI_STOCK_BOT_ENABLE_PAPER_WRITE_READINESS = "YES"
$env:AI_STOCK_BOT_PAPER_WRITE_READINESS_CONFIRMATION = "AUTHORIZE PAPER WRITE READINESS ONLY NO ORDER SUBMISSION"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V125_01_TO_V126_00_PAPER_WRITE_READINESS.ps1
```

Expected state:

```text
PAPER_WRITE_READY
```

This stage does not enable Live trading and does not submit, replace, or cancel any Paper order.

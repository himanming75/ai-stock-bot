# Actual Saved-Preview Final Approval

When the V137 preview is not ready, the runner returns `WAIT_PREVIEW_PACKAGE`.

When the preview is ready and deliberate approval is intended:

```powershell
$env:AI_STOCK_BOT_ENABLE_FINAL_PAPER_SUBMISSION_APPROVAL = "YES"
$env:AI_STOCK_BOT_FINAL_PAPER_SUBMISSION_APPROVAL_CONFIRMATION = "APPROVE EXACTLY ONE CONTROLLED ALPACA PAPER ORDER"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V137_01_TO_V138_00_ACTUAL_FINAL_PAPER_SUBMISSION_APPROVAL.ps1
```

This creates a local approval token only. It does not connect to Alpaca and cannot submit an order.

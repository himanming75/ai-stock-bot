# Runbook

```powershell
cd C:\stock-bot
powershell -ExecutionPolicy Bypass -File .\RUN_MARKET_INTELLIGENCE_DATA_FUSION_TEST_AND_VERIFY.ps1
```

Expected:

```text
Ran 5 tests
OK
VERIFY: PASS
NETWORK: OFF
BROKER WRITE: OFF
PAPER ORDERS: 0
LIVE ORDERS: 0
```

Output:

```text
release\market_intelligence_data_fusion\actual\market_intelligence_snapshot.json
```

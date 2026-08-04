# V321.01A Hotfix Release

## Problem
Windows PowerShell 5.1 `Set-Content -Encoding UTF8` can write a UTF-8 BOM. The Python policy loader used plain `utf-8`, so the policy could be treated as unreadable and fall back to an empty dictionary. This caused `POLICY_INVALID` and VERIFY FAIL after activation.

## Fix
- Read policy JSON using `utf-8-sig` so BOM and non-BOM UTF-8 are accepted.
- Save the activation policy with `System.Text.UTF8Encoding(false)`.
- Repair the existing policy as UTF-8 without BOM.
- Restore all safety flags: monitor-only, Paper/Live submission OFF, broker write OFF, live network OFF, maximum new orders 0.
- Add BOM regression test and dedicated hotfix verification.

## Safety
The hotfix contains no broker order submission path and submits zero Paper and zero Live orders.

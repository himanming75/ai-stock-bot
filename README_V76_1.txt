V76.1 Repository Functional Capability Audit

Purpose
-------
Audit the repository's 18 stable-release capabilities using the supplied
tracked-file and all-local-file inventories.

Important limitation
--------------------
This stage uses filename evidence only. A COMPLETE result means that matching
implementation, test, and release-evidence filenames were found. It does not
claim that behavior is correct or that all tests pass. Behavioral verification
is the next stage.

Inputs expected in repository root
----------------------------------
repository_files.txt
repository_all_files.txt

Test
----
python -m unittest tools.test_repository_functional_capability_audit_v76_1 -v

Run
---
python tools/repository_functional_capability_audit_v76_1.py `
  --tracked-files repository_files.txt `
  --all-files repository_all_files.txt `
  --config release/v76_1/config/repository_functional_capability_audit_config_v76_1.json `
  --output-dir release/v76_1/output

Safety
------
Offline only. No network, broker, orders, repository mutation, cash mutation,
position mutation, portfolio mutation, or live approval.

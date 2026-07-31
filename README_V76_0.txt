V76.0
Stable Release Transition & Functional Capability Baseline

Purpose
-------
Freeze V75.2BE as the Audit/Evidence Layer baseline without removing any
existing feature. Replace unlimited evidence-wrapper expansion with a
finite capability inventory, acceptance gates, and a prioritized functional
gap plan.

This stage does NOT claim that every project capability is complete.
The supplied inventory is deliberately conservative. Update each capability
only after repository evidence and tests confirm its actual state.

Test
----
python -m unittest tools.test_stable_release_functional_capability_baseline_v76_0 -v

Run
---
python tools/stable_release_functional_capability_baseline_v76_0.py `
  --inventory release/v76_0/config/functional_capability_inventory_input_v76_0.json `
  --config release/v76_0/config/stable_release_functional_capability_baseline_config_v76_0.json `
  --output-dir release/v76_0/output

Safety
------
This tool performs offline analysis only. It submits no paper or live orders,
does not connect to a broker or network, and mutates no cash, positions,
portfolio, or settlement state.

from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True)
class BrokerStatePaths:
    root: Path
    @property
    def canonical_root(self): return self.root/'release/p1_broker_consolidation/actual'
    @property
    def component_registry(self): return self.canonical_root/'canonical_component_registry.json'
    @property
    def compatibility_map(self): return self.canonical_root/'compatibility_map.json'
    @property
    def deprecation_manifest(self): return self.canonical_root/'deprecation_manifest.json'
    @property
    def order_registry(self): return self.canonical_root/'order_idempotency_registry.json'
    @property
    def order_ledger(self): return self.canonical_root/'order_ledger.jsonl'
    @property
    def fill_ledger(self): return self.canonical_root/'fill_ledger.jsonl'
    @property
    def portfolio_state(self): return self.canonical_root/'portfolio_state.json'
    @property
    def checkpoint(self): return self.canonical_root/'runtime_checkpoint.json'
    @property
    def kill_switch(self): return self.canonical_root/'kill_switch.json'
    @property
    def consolidation_result(self): return self.canonical_root/'broker_consolidation_result.json'

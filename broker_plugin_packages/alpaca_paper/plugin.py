from __future__ import annotations

class Plugin:
    read_only = True
    supports_orders = False

    def connect(self): return {"ok": True, "read_only": True}
    def disconnect(self): return {"ok": True}
    def get_account(self): return {}
    def get_positions(self): return []
    def get_orders(self): return []
    def health(self): return {"healthy": True, "read_only": True}
    def capabilities(self): return []
    def submit_order(self, payload):
        return {"ok": False, "error": "PLUGIN_ORDER_SUBMISSION_DISABLED", "actual_live_orders_submitted": 0}

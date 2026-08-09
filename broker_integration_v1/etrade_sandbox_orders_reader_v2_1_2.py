from __future__ import annotations


class ETradeSandboxOrdersReader:
    def __init__(self,readonly_transport):
        self.transport=readonly_transport

    def list_orders(self,account_id_key):
        path=f"/accounts/{account_id_key}/orders.json"
        return self.transport.get_json(path)

    def list_orders_safe(self,account_id_key):
        try:
            return {
                "status":"PASS",
                "payload":self.list_orders(account_id_key),
                "error":None,
            }
        except Exception as exc:
            return {
                "status":"READ_FAILED",
                "payload":{"OrdersResponse":{"Order":[]}},
                "error":type(exc).__name__,
            }

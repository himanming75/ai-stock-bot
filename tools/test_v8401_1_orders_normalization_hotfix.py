from __future__ import annotations
import unittest

from broker_sync.normalization import (
    normalize_snapshot,
)
from broker_sync.reconciliation import (
    reconcile_orders,
)


class Tests(unittest.TestCase):
    def test_string_order_is_ignored(self):
        snapshot = {
            "orders": [
                "OPEN",
                {
                    "order_id": "1",
                    "status": "OPEN",
                },
            ]
        }
        normalized = normalize_snapshot(snapshot)
        self.assertEqual(
            len(normalized["orders"]),
            1,
        )
        issues = reconcile_orders(
            normalized,
            {"orders": []},
            left_name="ALPACA",
            right_name="ETRADE",
        )
        self.assertEqual(len(issues), 1)

    def test_nested_etrade_order_extracted(self):
        payload = {
            "orders": {
                "account-key": {
                    "data": {
                        "OrdersResponse": {
                            "Order": [
                                {
                                    "orderId": "99",
                                    "status": "OPEN",
                                }
                            ]
                        }
                    }
                }
            }
        }
        normalized = normalize_snapshot(payload)
        self.assertEqual(
            len(normalized["orders"]),
            1,
        )
        self.assertEqual(
            normalized["orders"][0]["orderId"],
            "99",
        )

    def test_dictionary_map_does_not_crash(self):
        left = {
            "orders": {
                "account-a": {
                    "status": "OPEN"
                }
            }
        }
        right = {
            "orders": "OPEN"
        }
        issues = reconcile_orders(
            left,
            right,
            left_name="ALPACA",
            right_name="ETRADE",
        )
        self.assertEqual(len(issues), 1)

    def test_mixed_nested_values(self):
        payload = {
            "snapshot": {
                "accounts": [],
                "positions": [],
                "orders": [
                    "OPEN",
                    123,
                    None,
                    [
                        {
                            "order_id": "abc",
                            "status": "FILLED",
                        }
                    ],
                ],
                "quotes": [],
            }
        }
        normalized = normalize_snapshot(payload)
        self.assertEqual(
            normalized["orders"],
            [
                {
                    "order_id": "abc",
                    "status": "FILLED",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

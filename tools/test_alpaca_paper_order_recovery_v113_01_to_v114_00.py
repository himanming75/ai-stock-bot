from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from alpaca_broker import (
    AlpacaConfigurationError,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaPaperOrderRecoveryManager,
    AtomicPaperOrderRecoveryStore,
    BrokerOrder,
    PaperOrderRecoveryRecord,
    UrllibHttpTransport,
)


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")
        self.status = 200
        self.headers = {"X-Request-ID": "fixture-recovery"}

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class QueueOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payloads.pop(0))


def order_payload(status="filled", filled="1", symbol="AAPL", qty="1"):
    return {
        "id": "order-1",
        "client_order_id": "BOT-PAPER-ONE-000001",
        "symbol": symbol,
        "side": "buy",
        "qty": qty,
        "filled_qty": filled,
        "status": status,
    }


def broker_order(status="accepted", filled="0"):
    return BrokerOrder(
        order_id="order-1",
        client_order_id="BOT-PAPER-ONE-000001",
        symbol="AAPL",
        side="buy",
        quantity=Decimal("1"),
        filled_quantity=Decimal(filled),
        status=status,
    )


class AlpacaPaperOrderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "order_recovery.json"

    def tearDown(self):
        self.temp.cleanup()

    def manager(self, payloads, *, write=False):
        opener = QueueOpener(payloads)
        client = AlpacaPaperClient(
            config=AlpacaPaperConfig(
                network_read_enabled=True,
                network_write_enabled=write,
                max_retries=0,
            ),
            api_key="paper-key",
            secret_key="paper-secret",
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        manager = AlpacaPaperOrderRecoveryManager(
            client=client,
            store=AtomicPaperOrderRecoveryStore(self.path),
        )
        return manager, opener

    def test_write_enabled_client_rejected(self):
        with self.assertRaises(AlpacaConfigurationError):
            self.manager([], write=True)

    def test_atomic_store_round_trip(self):
        store = AtomicPaperOrderRecoveryStore(self.path)
        manager, _ = self.manager([])
        record = manager.checkpoint_from_order(broker_order())
        loaded = store.load()
        self.assertEqual(loaded.client_order_id, record.client_order_id)
        self.assertEqual(loaded.last_status, "accepted")

    def test_missing_checkpoint_rejected(self):
        manager, _ = self.manager([])
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()

    def test_recovery_to_filled(self):
        manager, opener = self.manager([order_payload("filled", "1")])
        manager.checkpoint_from_order(broker_order("partially_filled", "0.5"))
        report = manager.recover()
        self.assertEqual(report.previous_status, "partially_filled")
        self.assertEqual(report.recovered_status, "filled")
        self.assertTrue(report.terminal)
        self.assertEqual(report.recovery_generation, 1)
        self.assertEqual([r.get_method() for r, _ in opener.requests], ["GET"])

    def test_recovery_remains_active(self):
        manager, _ = self.manager([order_payload("accepted", "0")])
        manager.checkpoint_from_order(broker_order("accepted", "0"))
        report = manager.recover()
        self.assertFalse(report.terminal)
        self.assertEqual(report.recovered_status, "accepted")

    def test_duplicate_submission_prevented(self):
        manager, opener = self.manager([order_payload()])
        manager.checkpoint_from_order(broker_order())
        report = manager.recover()
        self.assertTrue(report.duplicate_submission_prevented)
        self.assertEqual(report.additional_orders_submitted, 0)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertNotIn("POST", [r.get_method() for r, _ in opener.requests])

    def test_generation_increments_across_restarts(self):
        manager, _ = self.manager([
            order_payload("partially_filled", "0.5"),
            order_payload("filled", "1"),
        ])
        manager.checkpoint_from_order(broker_order("accepted", "0"))
        first = manager.recover()
        second = manager.recover()
        self.assertEqual(first.recovery_generation, 1)
        self.assertEqual(second.recovery_generation, 2)

    def test_symbol_mismatch_rejected(self):
        manager, _ = self.manager([order_payload(symbol="SPY")])
        manager.checkpoint_from_order(broker_order())
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()

    def test_quantity_mismatch_rejected(self):
        manager, _ = self.manager([order_payload(qty="0.5")])
        manager.checkpoint_from_order(broker_order())
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()

    def test_filled_quantity_cannot_go_backwards(self):
        manager, _ = self.manager([order_payload("partially_filled", "0.25")])
        manager.checkpoint_from_order(broker_order("partially_filled", "0.5"))
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()

    def test_unknown_status_rejected(self):
        manager, _ = self.manager([order_payload("mystery", "0")])
        manager.checkpoint_from_order(broker_order())
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()

    def test_invalid_json_rejected(self):
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(AlpacaConfigurationError):
            AtomicPaperOrderRecoveryStore(self.path).load()

    def test_unconfirmed_submission_rejected(self):
        store = AtomicPaperOrderRecoveryStore(self.path)
        record = PaperOrderRecoveryRecord(
            schema_version=1,
            saved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            client_order_id="BOT-PAPER-ONE-000001",
            broker_order_id=None,
            symbol="AAPL",
            side="buy",
            requested_quantity=Decimal("1"),
            last_filled_quantity=Decimal("0"),
            last_status="unknown",
            submission_confirmed=False,
            terminal=False,
            recovery_generation=0,
        )
        store.save(record)
        manager, _ = self.manager([])
        with self.assertRaises(AlpacaConfigurationError):
            manager.recover()


if __name__ == "__main__":
    unittest.main()

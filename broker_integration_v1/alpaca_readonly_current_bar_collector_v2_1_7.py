from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from market_data_engine import AlpacaMessageParser, Bar, SubscriptionRegistry
from .etrade_current_market_data_signal_bridge_v2_1_7 import CurrentBarWindow


CONFIRMATION="CONNECT READ ONLY ALPACA CURRENT MARKET DATA"


@dataclass
class CollectorDiagnostics:
    connection_opened: bool=False
    auth_success_seen: bool=False
    subscription_seen: bool=False
    last_message_utc: str|None=None
    last_bar_utc: str|None=None
    raw_message_count: int=0
    parsed_bar_count: int=0


class AlpacaReadOnlyCurrentBarCollectorV217:
    def __init__(
        self,
        symbols,
        bars_per_symbol=3,
        progress_interval_seconds=10,
    ):
        self.symbols=sorted({
            str(x).upper().strip()
            for x in symbols
            if str(x).strip()
        })
        if not self.symbols:
            raise ValueError("At least one symbol is required.")

        self.bars_per_symbol=int(bars_per_symbol)
        if self.bars_per_symbol < 3 or self.bars_per_symbol > 50:
            raise ValueError(
                "bars_per_symbol must be between 3 and 50."
            )

        self.progress_interval_seconds=max(
            1,
            int(progress_interval_seconds),
        )
        self.parser=AlpacaMessageParser()
        self.window=CurrentBarWindow(
            max_bars_per_symbol=self.bars_per_symbol
        )
        self.done=threading.Event()
        self.errors=[]
        self.diag=CollectorDiagnostics()

    def complete(self):
        counts=self.window.counts()
        return all(
            counts.get(s,0)>=self.bars_per_symbol
            for s in self.symbols
        )

    def progress_line(self):
        counts=self.window.counts()
        parts=[
            f"{s} {counts.get(s,0)}/{self.bars_per_symbol}"
            for s in self.symbols
        ]
        return " | ".join(parts)

    def diagnostic_snapshot(self):
        return {
            "connection_opened":self.diag.connection_opened,
            "auth_success_seen":self.diag.auth_success_seen,
            "subscription_seen":self.diag.subscription_seen,
            "last_message_utc":self.diag.last_message_utc,
            "last_bar_utc":self.diag.last_bar_utc,
            "raw_message_count":self.diag.raw_message_count,
            "parsed_bar_count":self.diag.parsed_bar_count,
            "counts":self.window.counts(),
            "target_bars_per_symbol":self.bars_per_symbol,
        }

    def _print_waiting_diagnostic(self,elapsed_seconds):
        print(
            f"[WAITING {int(elapsed_seconds)}s] "
            +self.progress_line()
        )
        if (
            self.diag.connection_opened
            and self.diag.parsed_bar_count==0
        ):
            print(
                "  WebSocket connected, but no current bars received yet. "
                "The market may be closed, the selected feed may be idle, "
                "or no eligible bar has been published."
            )
        elif not self.diag.connection_opened:
            print(
                "  Waiting for Alpaca WebSocket connection..."
            )

    def collect(self,timeout_seconds=900):
        key=os.environ.get("APCA_API_KEY_ID")
        secret=os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError(
                "Alpaca read-only market-data credentials are required."
            )

        try:
            import websocket
        except ImportError as exc:
            raise RuntimeError(
                "websocket-client is required. "
                "Install with: python -m pip install websocket-client"
            ) from exc

        registry=SubscriptionRegistry()
        registry.subscribe(bars=self.symbols)

        url="wss://stream.data.alpaca.markets/v2/iex"
        auth={
            "action":"auth",
            "key":key,
            "secret":secret,
        }
        subscribe=registry.alpaca_subscribe_message()

        def on_open(ws):
            self.diag.connection_opened=True
            print("ALPACA WEBSOCKET: CONNECTED")
            print(
                "SUBSCRIBING BARS:",
                ", ".join(self.symbols),
            )
            ws.send(json.dumps(auth))
            ws.send(json.dumps(subscribe))

        def on_message(ws,message):
            try:
                self.diag.raw_message_count+=1
                self.diag.last_message_utc=(
                    datetime.now(timezone.utc).isoformat()
                )

                payload=json.loads(message)

                raw_rows=payload if isinstance(payload,list) else [payload]
                for raw in raw_rows:
                    if isinstance(raw,dict):
                        if (
                            raw.get("T")=="success"
                            and raw.get("msg")=="authenticated"
                        ):
                            self.diag.auth_success_seen=True
                            print("ALPACA AUTH: PASS")
                        elif raw.get("T")=="subscription":
                            self.diag.subscription_seen=True
                            print("ALPACA SUBSCRIPTION: PASS")

                for item in self.parser.parse_frame(payload):
                    if (
                        isinstance(item,Bar)
                        and item.symbol in self.symbols
                    ):
                        self.window.add(item)
                        self.diag.parsed_bar_count+=1
                        self.diag.last_bar_utc=(
                            datetime.now(timezone.utc).isoformat()
                        )
                        print(
                            "BAR RECEIVED:",
                            item.symbol,
                            item.timestamp.isoformat(),
                            f"close={item.close}",
                            "|",
                            self.progress_line(),
                        )

                if self.complete():
                    self.done.set()
                    ws.close()

            except Exception as exc:
                self.errors.append(
                    f"{type(exc).__name__}: {exc}"
                )
                self.done.set()
                ws.close()

        def on_error(ws,error):
            self.errors.append(str(error))
            self.done.set()

        def on_close(ws,status_code,msg):
            if not self.complete() and not self.errors:
                print(
                    "ALPACA WEBSOCKET: CLOSED "
                    f"status={status_code} message={msg}"
                )

        app=websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        thread=threading.Thread(
            target=app.run_forever,
            daemon=True,
        )
        thread.start()

        timeout_seconds=max(1,int(timeout_seconds))
        started=time.monotonic()
        next_progress=0.0

        while not self.done.is_set():
            elapsed=time.monotonic()-started

            if elapsed >= timeout_seconds:
                break

            if elapsed >= next_progress:
                self._print_waiting_diagnostic(elapsed)
                next_progress=elapsed+self.progress_interval_seconds

            self.done.wait(timeout=1.0)

        if thread.is_alive():
            try:
                app.close()
            except Exception:
                pass

        if self.errors:
            raise RuntimeError(
                "Alpaca market-data stream error: "
                +"; ".join(self.errors)
            )

        if not self.complete():
            snap=self.diagnostic_snapshot()

            print("")
            print("=== CURRENT MARKET DATA WAIT TIMEOUT ===")
            print("BAR PROGRESS:",self.progress_line())
            print(
                "WEBSOCKET CONNECTED:",
                snap["connection_opened"],
            )
            print(
                "AUTH SUCCESS SEEN:",
                snap["auth_success_seen"],
            )
            print(
                "SUBSCRIPTION SEEN:",
                snap["subscription_seen"],
            )
            print(
                "RAW MESSAGES:",
                snap["raw_message_count"],
            )
            print(
                "PARSED BARS:",
                snap["parsed_bar_count"],
            )
            print(
                "LAST MESSAGE UTC:",
                snap["last_message_utc"],
            )
            print(
                "LAST BAR UTC:",
                snap["last_bar_utc"],
            )
            print(
                "Interpretation: no sufficient current bars arrived "
                "before timeout. If connected/authenticated, the market "
                "may be closed or the selected feed may currently have "
                "no eligible bar updates."
            )
            raise TimeoutError(
                "Timed out before enough current bars were collected. "
                f"Counts={self.window.counts()}"
            )

        print("")
        print("CURRENT BAR COLLECTION: PASS")
        print("FINAL PROGRESS:",self.progress_line())

        return (
            self.window.bars(),
            self.window.counts(),
        )

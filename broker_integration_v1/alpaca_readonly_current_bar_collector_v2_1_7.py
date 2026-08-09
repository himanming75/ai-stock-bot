from __future__ import annotations

import json
import os
import threading
import time

from market_data_engine import AlpacaMessageParser, Bar, SubscriptionRegistry
from .etrade_current_market_data_signal_bridge_v2_1_7 import CurrentBarWindow


CONFIRMATION="CONNECT READ ONLY ALPACA CURRENT MARKET DATA"


class AlpacaReadOnlyCurrentBarCollectorV217:
    def __init__(self,symbols,bars_per_symbol=3):
        self.symbols=sorted({str(x).upper().strip() for x in symbols if str(x).strip()})
        if not self.symbols:
            raise ValueError("At least one symbol is required.")
        self.bars_per_symbol=int(bars_per_symbol)
        if self.bars_per_symbol < 3 or self.bars_per_symbol > 50:
            raise ValueError("bars_per_symbol must be between 3 and 50.")
        self.parser=AlpacaMessageParser()
        self.window=CurrentBarWindow(max_bars_per_symbol=self.bars_per_symbol)
        self.done=threading.Event()
        self.errors=[]

    def complete(self):
        counts=self.window.counts()
        return all(counts.get(s,0)>=self.bars_per_symbol for s in self.symbols)

    def collect(self,timeout_seconds=900):
        key=os.environ.get("APCA_API_KEY_ID")
        secret=os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Alpaca read-only market-data credentials are required.")

        try:
            import websocket
        except ImportError as exc:
            raise RuntimeError("websocket-client is required.") from exc

        registry=SubscriptionRegistry()
        registry.subscribe(bars=self.symbols)

        url="wss://stream.data.alpaca.markets/v2/iex"
        auth={"action":"auth","key":key,"secret":secret}
        subscribe=registry.alpaca_subscribe_message()

        def on_open(ws):
            ws.send(json.dumps(auth))
            ws.send(json.dumps(subscribe))

        def on_message(ws,message):
            try:
                payload=json.loads(message)
                for item in self.parser.parse_frame(payload):
                    if isinstance(item,Bar) and item.symbol in self.symbols:
                        self.window.add(item)
                if self.complete():
                    self.done.set()
                    ws.close()
            except Exception as exc:
                self.errors.append(f"{type(exc).__name__}: {exc}")
                self.done.set()
                ws.close()

        def on_error(ws,error):
            self.errors.append(str(error))
            self.done.set()

        app=websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
        )

        thread=threading.Thread(target=app.run_forever,daemon=True)
        thread.start()
        self.done.wait(timeout=max(1,int(timeout_seconds)))
        if thread.is_alive():
            try:
                app.close()
            except Exception:
                pass
        if self.errors:
            raise RuntimeError("; ".join(self.errors))
        if not self.complete():
            raise TimeoutError(
                f"Timed out before enough current bars were collected. Counts={self.window.counts()}"
            )
        return self.window.bars(), self.window.counts()

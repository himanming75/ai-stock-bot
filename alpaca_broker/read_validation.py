from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .client import AlpacaPaperClient
from .config import AlpacaPaperConfig, CredentialLoader
from .errors import AlpacaConfigurationError
from .reconciliation import BrokerPortfolioReconciler
from portfolio_engine import PortfolioSnapshot


READ_OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ALPACA_PAPER_READ"
READ_CONFIRMATION_ENV = "AI_STOCK_BOT_ALPACA_PAPER_READ_CONFIRMATION"
READ_CONFIRMATION_TEXT = "READ MY ALPACA PAPER ACCOUNT ONLY"


@dataclass(frozen=True)
class ControlledReadReport:
    generated_at: datetime
    paper_base_url: str
    account_id_redacted: str
    account_status: str
    trading_blocked: bool
    cash: Decimal
    equity: Decimal
    buying_power: Decimal
    market_is_open: bool
    clock_timestamp: datetime
    next_open: datetime
    next_close: datetime
    position_count: int
    open_order_count: int
    closed_order_count: int
    reconciliation_matched: bool | None
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int = 0
    live_orders_submitted: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = str(value)
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


class ControlledPaperReadValidator:
    def __init__(self, client: AlpacaPaperClient) -> None:
        self.client = client

    @staticmethod
    def validate_opt_in(environ: dict[str, str]) -> None:
        if environ.get(READ_OPT_IN_ENV, "").strip().upper() != "YES":
            raise AlpacaConfigurationError(
                f"{READ_OPT_IN_ENV}=YES is required for actual paper reads"
            )
        if environ.get(READ_CONFIRMATION_ENV, "").strip() != READ_CONFIRMATION_TEXT:
            raise AlpacaConfigurationError(
                f"{READ_CONFIRMATION_ENV} must equal: {READ_CONFIRMATION_TEXT}"
            )

    @classmethod
    def from_environment(
        cls,
        environ: dict[str, str],
        *,
        transport,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> "ControlledPaperReadValidator":
        cls.validate_opt_in(environ)
        key, secret = CredentialLoader().load(environ)
        config = AlpacaPaperConfig(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            network_read_enabled=True,
            network_write_enabled=False,
        )
        return cls(AlpacaPaperClient(
            config=config,
            api_key=key,
            secret_key=secret,
            transport=transport,
        ))

    def run(
        self,
        *,
        internal_portfolio: PortfolioSnapshot | None = None,
        closed_order_limit: int = 50,
    ) -> ControlledReadReport:
        account = self.client.get_account()
        clock = self.client.get_clock()
        positions = self.client.list_positions()
        open_orders = self.client.list_orders(status="open", limit=50)
        closed_orders = self.client.list_orders(
            status="closed", limit=closed_order_limit
        )

        reconciliation_matched = None
        if internal_portfolio is not None:
            reconciliation_matched = BrokerPortfolioReconciler().reconcile(
                internal=internal_portfolio,
                account=account,
                positions=positions,
            ).matched

        return ControlledReadReport(
            generated_at=datetime.now(timezone.utc),
            paper_base_url=self.client.config.base_url,
            account_id_redacted=CredentialLoader.redact(account.account_id),
            account_status=account.status,
            trading_blocked=account.trading_blocked,
            cash=account.cash,
            equity=account.equity,
            buying_power=account.buying_power,
            market_is_open=clock.is_open,
            clock_timestamp=clock.timestamp,
            next_open=clock.next_open,
            next_close=clock.next_close,
            position_count=len(positions),
            open_order_count=len(open_orders),
            closed_order_count=len(closed_orders),
            reconciliation_matched=reconciliation_matched,
            network_requests_executed=self.client.network_requests_executed,
            write_requests_executed=self.client.write_requests_executed,
        )

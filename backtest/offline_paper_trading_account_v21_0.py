import hashlib
import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_verification_final_report_v20_0 import (
    SandboxVerificationFinalReportV200Result,
    verify_final_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_trading_account_v21_0"
)
REQUIRED_ACCOUNT_TEXT = "CREATE IN MEMORY OFFLINE PAPER ACCOUNT V21.0"


@dataclass(frozen=True)
class OfflinePaperTradingAccountV210Policy:
    required_source_version: str = "V20.0"
    required_source_status: str = "FINALIZED_IN_MEMORY"
    required_source_verification_status: str = "SANDBOX_VERIFICATION_COMPLETE"
    required_confirmation_text: str = REQUIRED_ACCOUNT_TEXT
    required_currency: str = "USD"
    minimum_initial_cash: float = 1.0
    maximum_initial_cash: float = 1_000_000.0
    require_operator: bool = True
    require_empty_positions: bool = True
    require_source_unchanged: bool = True
    offline_only: bool = True
    deposits_disabled: bool = True
    withdrawals_disabled: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_api_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperPositionV210:
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_profit_loss: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperTradingAccountV210:
    account_id: str
    created_at: str
    account_mode: str
    account_status: str
    currency: str
    operator: str
    initial_cash: float
    cash_balance: float
    reserved_cash: float
    positions_market_value: float
    total_equity: float
    realized_profit_loss: float
    unrealized_profit_loss: float
    total_profit_loss: float
    source_v20_result_id: str
    source_v20_report_id: str
    source_v20_report_hash: str
    positions: tuple[OfflinePaperPositionV210, ...]
    paper_trading_enabled: bool
    paper_order_execution_authorized: bool
    automatic_execution_authorized: bool
    deposits_authorized: bool
    withdrawals_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    account_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("account_hash", None)
        payload["positions"] = [
            position.to_dict() for position in self.positions
        ]
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["account_hash"] = self.account_hash
        return payload


@dataclass
class OfflinePaperTradingAccountV210Result:
    version: str
    created_at: str
    account_result_id: str
    result_status: str
    result_status_label: str
    source_v20_result_id: str | None
    source_v20_report_hash: str | None
    account_id: str | None
    account_hash: str | None
    account_mode: str
    currency: str | None
    initial_cash: float
    cash_balance: float
    total_equity: float
    total_position_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    source_linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    account_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    account_created: bool
    paper_trading_enabled: bool
    paper_order_execution_authorized: bool
    automatic_execution_authorized: bool
    deposits_authorized: bool
    withdrawals_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    account_policy: OfflinePaperTradingAccountV210Policy
    account: OfflinePaperTradingAccountV210 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["account_policy"] = self.account_policy.to_dict()
        payload["account"] = self.account.to_dict() if self.account else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_policy(
    policy: OfflinePaperTradingAccountV210Policy,
) -> list[str]:
    if not isinstance(policy, OfflinePaperTradingAccountV210Policy):
        return ["Offline Paper Trading Account Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V20.0",
        "required_source_status": "FINALIZED_IN_MEMORY",
        "required_source_verification_status": "SANDBOX_VERIFICATION_COMPLETE",
        "required_confirmation_text": REQUIRED_ACCOUNT_TEXT,
        "required_currency": "USD",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.0 기준과 다릅니다.")
    if (
        not _valid_money(policy.minimum_initial_cash)
        or not _valid_money(policy.maximum_initial_cash)
        or policy.minimum_initial_cash <= 0
        or policy.maximum_initial_cash < policy.minimum_initial_cash
    ):
        errors.append("초기 가상 현금 한도가 올바르지 않습니다.")
    for name in (
        "require_operator",
        "require_empty_positions",
        "require_source_unchanged",
        "offline_only",
        "deposits_disabled",
        "withdrawals_disabled",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_api_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V21.0에서 True여야 합니다.")
    return errors


def _valid_money(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _safe_source(source: SandboxVerificationFinalReportV200Result) -> bool:
    return not any(
        (
            source.paper_execution_authorized,
            source.automatic_execution_authorized,
            not source.execution_blocked,
            source.credentials_used,
            source.market_data_api_called,
            source.network_accessed,
            source.account_accessed,
            source.broker_api_called,
            source.broker_order_created,
            source.order_submitted,
            source.live_order_created,
            source.live_execution_authorized,
        )
    )


def verify_offline_paper_account(
    account: OfflinePaperTradingAccountV210,
) -> tuple[bool, list[str]]:
    if not isinstance(account, OfflinePaperTradingAccountV210):
        return False, ["Offline Paper Account 형식 오류입니다."]
    errors: list[str] = []
    if account.account_mode != "OFFLINE_PAPER":
        errors.append("Account Mode가 OFFLINE_PAPER가 아닙니다.")
    if account.account_status != "READY_IN_MEMORY":
        errors.append("Account Status가 올바르지 않습니다.")
    if account.currency != "USD":
        errors.append("Account Currency가 USD가 아닙니다.")
    if account.positions:
        errors.append("신규 Offline Paper Account의 Position은 비어 있어야 합니다.")
    if not all(
        (
            account.initial_cash == account.cash_balance,
            account.reserved_cash == 0.0,
            account.positions_market_value == 0.0,
            account.total_equity == account.initial_cash,
            account.realized_profit_loss == 0.0,
            account.unrealized_profit_loss == 0.0,
            account.total_profit_loss == 0.0,
            account.paper_trading_enabled,
            not account.paper_order_execution_authorized,
            not account.automatic_execution_authorized,
            not account.deposits_authorized,
            not account.withdrawals_authorized,
            account.execution_blocked,
            not account.credentials_used,
            not account.market_data_api_called,
            not account.account_api_called,
            not account.network_accessed,
            not account.broker_api_called,
            not account.order_submitted,
            not account.live_execution_authorized,
        )
    ):
        errors.append("Offline Paper Account 초기 상태 또는 안전장치 오류입니다.")
    if account.account_hash != sha256_payload(account.payload_without_hash()):
        errors.append("Offline Paper Account Hash가 일치하지 않습니다.")
    return not errors, errors


def _result(
    policy_value: OfflinePaperTradingAccountV210Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    account: OfflinePaperTradingAccountV210 | None = None,
    source_result: SandboxVerificationFinalReportV200Result | None = None,
    **checks: bool,
) -> OfflinePaperTradingAccountV210Result:
    created = status == "CREATED_IN_MEMORY" and account is not None
    return OfflinePaperTradingAccountV210Result(
        version="V21.0",
        created_at=now.isoformat(),
        account_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Trading Account 생성 완료"
            if created
            else "Offline Paper Trading Account 차단"
            if status == "BLOCKED"
            else "Offline Paper Trading Account 실패"
        ),
        source_v20_result_id=(
            source_result.final_report_result_id if source_result else None
        ),
        source_v20_report_hash=(
            source_result.report_hash if source_result else None
        ),
        account_id=account.account_id if account else None,
        account_hash=account.account_hash if account else None,
        account_mode="OFFLINE_PAPER",
        currency=account.currency if account else None,
        initial_cash=account.initial_cash if account else 0.0,
        cash_balance=account.cash_balance if account else 0.0,
        total_equity=account.total_equity if account else 0.0,
        total_position_count=len(account.positions) if account else 0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        account_hash_checks_passed=checks.get("hash", False),
        safety_checks_passed=True,
        all_checks_passed=created,
        account_created=created,
        paper_trading_enabled=created,
        paper_order_execution_authorized=False,
        automatic_execution_authorized=False,
        deposits_authorized=False,
        withdrawals_authorized=False,
        execution_blocked=True,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        account_policy=policy_value,
        account=account,
        reasons=reasons,
        warnings=[
            "V21.0은 가상 잔액만 생성하며 주문 체결 기능을 포함하지 않습니다.",
            "Broker API, 실제 계좌, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.1 Offline Paper Order Model 단계에서 가상 주문 구조를 추가합니다."
        ],
    )


def create_offline_paper_trading_account_v21_0(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    initial_cash: Any = 10_000.0,
    currency: Any = "USD",
    positions: Any = None,
    policy: OfflinePaperTradingAccountV210Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperTradingAccountV210Result:
    policy = policy or OfflinePaperTradingAccountV210Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    if policy_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperTradingAccountV210Policy)
            else OfflinePaperTradingAccountV210Policy()
        )
        return _result(safe_policy, now, "BLOCKED", policy_errors)
    if not isinstance(source, SandboxVerificationFinalReportV200Result):
        return _result(
            policy,
            now,
            "FAILED",
            ["Source는 V20.0 Sandbox Verification Final Report Result여야 합니다."],
            policy=True,
        )
    source_before = canonical_json(source.to_dict())
    source_errors: list[str] = []
    if source.version != policy.required_source_version:
        source_errors.append("V20.0 Source Version이 아닙니다.")
    if source.result_status != policy.required_source_status:
        source_errors.append("V20.0 Final Report가 완료 상태가 아닙니다.")
    if (
        source.final_verification_status
        != policy.required_source_verification_status
    ):
        source_errors.append("V20.0 Sandbox Verification 완료 상태가 아닙니다.")
    if source.report is None or not source.report_hash:
        source_errors.append("V20.0 Final Report가 없습니다.")
    else:
        valid_report, report_errors = verify_final_report(source.report)
        if not valid_report or report_errors:
            source_errors.append("V20.0 Final Report Hash 검증 실패입니다.")
        if source.report_hash != source.report.report_hash:
            source_errors.append("V20.0 Result와 Report Hash 연결 오류입니다.")
    if not source.all_checks_passed or not _safe_source(source):
        source_errors.append("V20.0 Source 안전장치 검증 실패입니다.")
    if source_errors:
        return _result(
            policy,
            now,
            "FAILED",
            source_errors,
            source_result=source,
            policy=True,
            input=True,
        )
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("V21.0 확인 문구가 일치하지 않습니다.")
    if not _valid_money(initial_cash):
        input_errors.append("Initial Cash는 유한한 숫자여야 합니다.")
    else:
        initial_cash = round(float(initial_cash), 2)
        if not (
            policy.minimum_initial_cash
            <= initial_cash
            <= policy.maximum_initial_cash
        ):
            input_errors.append("Initial Cash가 V21.0 허용 범위를 벗어났습니다.")
    if currency != policy.required_currency:
        input_errors.append("V21.0 Currency는 USD만 허용됩니다.")
    if positions not in (None, (), []):
        input_errors.append("신규 V21.0 Account는 Position 없이 시작해야 합니다.")
    try:
        source_created_at = datetime.fromisoformat(source.created_at)
        if now < source_created_at:
            input_errors.append("Account 생성 시간이 V20.0보다 이전입니다.")
    except (TypeError, ValueError):
        input_errors.append("V20.0 Source 시간이 올바르지 않습니다.")
    if input_errors:
        return _result(
            policy,
            now,
            "BLOCKED",
            input_errors,
            source_result=source,
            policy=True,
            source=True,
            linkage=True,
        )
    payload = {
        "account_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "account_mode": "OFFLINE_PAPER",
        "account_status": "READY_IN_MEMORY",
        "currency": "USD",
        "operator": operator.strip(),
        "initial_cash": initial_cash,
        "cash_balance": initial_cash,
        "reserved_cash": 0.0,
        "positions_market_value": 0.0,
        "total_equity": initial_cash,
        "realized_profit_loss": 0.0,
        "unrealized_profit_loss": 0.0,
        "total_profit_loss": 0.0,
        "source_v20_result_id": source.final_report_result_id,
        "source_v20_report_id": source.report_id,
        "source_v20_report_hash": source.report_hash,
        "positions": (),
        "paper_trading_enabled": True,
        "paper_order_execution_authorized": False,
        "automatic_execution_authorized": False,
        "deposits_authorized": False,
        "withdrawals_authorized": False,
        "execution_blocked": True,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    hash_payload = dict(payload)
    hash_payload["positions"] = []
    account = OfflinePaperTradingAccountV210(
        **payload,
        account_hash=sha256_payload(hash_payload),
    )
    valid_account, account_errors = verify_offline_paper_account(account)
    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _result(
            policy,
            now,
            "FAILED",
            ["V21.0 생성 중 V20.0 Source가 변경되었습니다."],
            source_result=source,
            policy=True,
            input=True,
            source=True,
            linkage=True,
        )
    if not valid_account:
        return _result(
            policy,
            now,
            "FAILED",
            account_errors,
            source_result=source,
            policy=True,
            input=True,
            source=True,
            linkage=True,
            unchanged=True,
        )
    return _result(
        policy,
        now,
        "CREATED_IN_MEMORY",
        [],
        account=account,
        source_result=source,
        policy=True,
        input=True,
        source=True,
        linkage=True,
        unchanged=True,
        hash=True,
    )


def save_account_result(
    result: OfflinePaperTradingAccountV210Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "-").replace("+", "_")
    report_path = output_directory / f"offline_paper_account_{stamp}.json"
    latest_path = output_directory / "latest.json"
    text = json.dumps(
        result.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_account_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

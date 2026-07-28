"""V23.3 Offline Paper Portfolio Validation Ledger.

Records immutable, in-memory validation certificates for a verified V23.2
portfolio update. This module has no network, broker, account API, credential,
order-submission, or live-execution capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


VERSION = "V23.3"
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER PORTFOLIO VALIDATION V23.3"
OUTPUT_DIRECTORY = Path("backtest_outputs")
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class PortfolioValidationLedgerV233Policy:
    required_source_version: str = "V23.2"
    allowed_source_statuses: tuple[str, ...] = (
        "UPDATED_IN_MEMORY",
        "NO_CHANGE_IN_MEMORY",
    )
    required_confirmation_text: str = CONFIRMATION_TEXT
    source_mutation_disabled: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_api_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    broker_order_creation_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioValidationEntryV233:
    validation_id: str
    sequence: int
    created_at: str
    previous_entry_hash: str
    source_update_result_id: str
    source_portfolio_snapshot_id: str
    source_portfolio_hash: str
    operator: str
    validation_status: str
    finding: str
    source_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioValidationLedgerV233:
    ledger_id: str
    created_at: str
    source_update_result_id: str
    source_portfolio_snapshot_id: str
    source_portfolio_hash: str
    entries: tuple[PortfolioValidationEntryV233, ...]
    ledger_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("ledger_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


@dataclass
class PortfolioValidationLedgerV233Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    source_update_result_id: str | None
    source_portfolio_hash: str | None
    ledger_id: str | None
    ledger_hash: str | None
    entry_recorded: bool
    policy_checks_passed: bool
    source_checks_passed: bool
    accounting_checks_passed: bool
    source_unchanged_checks_passed: bool
    ledger_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    funds_reserved: bool
    holdings_reserved: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    validation_policy: PortfolioValidationLedgerV233Policy
    ledger: PortfolioValidationLedgerV233 | None
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_policy"] = self.validation_policy.to_dict()
        payload["ledger"] = self.ledger.to_dict() if self.ledger else None
        return payload


def canonical_json(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def _safe(value: Any) -> bool:
    names = (
        "funds_reserved", "holdings_reserved", "transmit", "credentials_used",
        "market_data_api_called", "account_api_called", "network_accessed",
        "broker_api_called", "broker_order_created", "order_submitted",
        "live_execution_authorized",
    )
    return all(getattr(value, name, False) is False for name in names)


def validate_policy(policy: PortfolioValidationLedgerV233Policy) -> list[str]:
    if not isinstance(policy, PortfolioValidationLedgerV233Policy):
        return ["V23.3 Policy 형식 오류입니다."]
    errors = []
    if policy.required_source_version != "V23.2":
        errors.append("Source Version 정책 오류입니다.")
    if policy.allowed_source_statuses != ("UPDATED_IN_MEMORY", "NO_CHANGE_IN_MEMORY"):
        errors.append("Source Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("확인 문구 정책 오류입니다.")
    for name, value in policy.to_dict().items():
        if name.endswith(("_disabled", "_forbidden")) and value is not True:
            errors.append(f"{name}는 True여야 합니다.")
    return errors


def _source_errors(source: Any, policy: PortfolioValidationLedgerV233Policy) -> list[str]:
    errors = []
    if getattr(source, "version", None) != policy.required_source_version:
        errors.append("V23.2 Source Version 오류입니다.")
    if getattr(source, "result_status", None) not in policy.allowed_source_statuses:
        errors.append("V23.2 Source 상태 오류입니다.")
    if getattr(source, "all_checks_passed", None) is not True:
        errors.append("V23.2 Source 검증이 완료되지 않았습니다.")
    portfolio = getattr(source, "portfolio", None)
    if portfolio is None:
        return errors + ["V23.2 Portfolio가 없습니다."]
    payload = portfolio.payload_without_hash() if hasattr(portfolio, "payload_without_hash") else {}
    actual_hash = getattr(portfolio, "portfolio_hash", None)
    if not payload or sha256_payload(payload) != actual_hash:
        errors.append("V23.2 Portfolio Hash 검증에 실패했습니다.")
    if getattr(source, "portfolio_hash", None) != actual_hash:
        errors.append("V23.2 Result 연결 Hash 오류입니다.")
    if not _safe(source) or not _safe(portfolio):
        errors.append("V23.2 안전 플래그 오류입니다.")
    return errors


def _accounting_errors(portfolio: Any) -> list[str]:
    errors = []
    try:
        cash = float(portfolio.cash_balance)
        market_value = float(portfolio.positions_market_value)
        equity = float(portfolio.total_equity)
        positions = tuple(portfolio.positions)
    except (AttributeError, TypeError, ValueError):
        return ["Portfolio 회계 필드 오류입니다."]
    if cash < 0 or market_value < 0 or equity < 0:
        errors.append("Portfolio 음수 금액 오류입니다.")
    if abs((cash + market_value) - equity) > 0.011:
        errors.append("Portfolio Equity 계산 오류입니다.")
    symbols = []
    calculated = 0.0
    for position in positions:
        symbol = getattr(position, "symbol", "")
        quantity = float(getattr(position, "quantity", -1))
        average = float(getattr(position, "average_cost", -1))
        last_price = float(getattr(position, "last_fill_price", -1))
        basis = float(getattr(position, "cost_basis", -1))
        if not symbol or quantity <= 0 or min(average, last_price, basis) < 0:
            errors.append("Portfolio Position 값 오류입니다.")
        if abs(quantity * average - basis) > 0.011:
            errors.append("Portfolio Cost Basis 오류입니다.")
        symbols.append(symbol)
        calculated += quantity * last_price
    if len(symbols) != len(set(symbols)):
        errors.append("Portfolio Symbol 중복 오류입니다.")
    if abs(calculated - market_value) > 0.011:
        errors.append("Portfolio Market Value 계산 오류입니다.")
    return errors


def verify_portfolio_validation_ledger(ledger: PortfolioValidationLedgerV233) -> list[str]:
    if not isinstance(ledger, PortfolioValidationLedgerV233):
        return ["V23.3 Ledger 형식 오류입니다."]
    errors = []
    previous = GENESIS_HASH
    previous_time = None
    seen_source_hashes = set()
    for expected, entry in enumerate(ledger.entries, 1):
        if entry.sequence != expected:
            errors.append("Ledger Sequence 오류입니다.")
        if entry.previous_entry_hash != previous:
            errors.append("Ledger Chain 연결 오류입니다.")
        if sha256_payload(entry.payload_without_hash()) != entry.entry_hash:
            errors.append("Ledger Entry Hash 오류입니다.")
        current_time = _parse_utc(entry.created_at)
        if previous_time and current_time < previous_time:
            errors.append("Ledger 시간 역행 오류입니다.")
        if entry.source_portfolio_hash in seen_source_hashes:
            errors.append("중복 Portfolio 검증 기록입니다.")
        seen_source_hashes.add(entry.source_portfolio_hash)
        previous, previous_time = entry.entry_hash, current_time
    if sha256_payload(ledger.payload_without_hash()) != ledger.ledger_hash:
        errors.append("Ledger Snapshot Hash 오류입니다.")
    return errors


def record_portfolio_validation_v23_3(
    source: Any,
    operator: str,
    confirmation: str,
    *,
    existing_ledger: PortfolioValidationLedgerV233 | None = None,
    policy: PortfolioValidationLedgerV233Policy | None = None,
    now: datetime | None = None,
) -> PortfolioValidationLedgerV233Result:
    policy = policy or PortfolioValidationLedgerV233Policy()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    created_at = now.isoformat()
    source_before = canonical_json(source)
    errors = validate_policy(policy)
    if not isinstance(operator, str) or not operator.strip():
        errors.append("Operator가 필요합니다.")
    if confirmation != policy.required_confirmation_text:
        errors.append("확인 문구가 일치하지 않습니다.")
    source_errors = _source_errors(source, policy)
    portfolio = getattr(source, "portfolio", None)
    accounting_errors = _accounting_errors(portfolio) if portfolio else []
    ledger_errors = verify_portfolio_validation_ledger(existing_ledger) if existing_ledger else []
    errors.extend(source_errors + accounting_errors + ledger_errors)
    source_hash = getattr(source, "portfolio_hash", None)
    if existing_ledger:
        if any(entry.source_portfolio_hash == source_hash for entry in existing_ledger.entries):
            errors.append("중복 Portfolio 검증은 차단됩니다.")
        if existing_ledger.entries and now < _parse_utc(existing_ledger.entries[-1].created_at):
            errors.append("Ledger 시간 역행은 차단됩니다.")
    ledger = None
    if not errors:
        old_entries = existing_ledger.entries if existing_ledger else ()
        previous_hash = old_entries[-1].entry_hash if old_entries else GENESIS_HASH
        payload = {
            "validation_id": str(uuid.uuid4()),
            "sequence": len(old_entries) + 1,
            "created_at": created_at,
            "previous_entry_hash": previous_hash,
            "source_update_result_id": source.update_result_id,
            "source_portfolio_snapshot_id": portfolio.portfolio_snapshot_id,
            "source_portfolio_hash": source_hash,
            "operator": operator.strip(),
            "validation_status": "VERIFIED_OFFLINE",
            "finding": "PORTFOLIO_ACCOUNTING_AND_SAFETY_VALID",
            "source_mutated": False,
            "funds_reserved": False,
            "holdings_reserved": False,
            "transmit": False,
            "credentials_used": False,
            "market_data_api_called": False,
            "account_api_called": False,
            "network_accessed": False,
            "broker_api_called": False,
            "broker_order_created": False,
            "order_submitted": False,
            "live_execution_authorized": False,
        }
        entry = PortfolioValidationEntryV233(**payload, entry_hash=sha256_payload(payload))
        entries = old_entries + (entry,)
        ledger_payload = {
            "ledger_id": existing_ledger.ledger_id if existing_ledger else str(uuid.uuid4()),
            "created_at": existing_ledger.created_at if existing_ledger else created_at,
            "source_update_result_id": source.update_result_id,
            "source_portfolio_snapshot_id": portfolio.portfolio_snapshot_id,
            "source_portfolio_hash": source_hash,
            "entries": [item.to_dict() for item in entries],
        }
        ledger = PortfolioValidationLedgerV233(
            ledger_id=ledger_payload["ledger_id"],
            created_at=ledger_payload["created_at"],
            source_update_result_id=ledger_payload["source_update_result_id"],
            source_portfolio_snapshot_id=ledger_payload["source_portfolio_snapshot_id"],
            source_portfolio_hash=ledger_payload["source_portfolio_hash"],
            entries=entries,
            ledger_hash=sha256_payload(ledger_payload),
        )
    unchanged = source_before == canonical_json(source)
    if not unchanged:
        errors.append("V23.2 Source가 변경되었습니다.")
        ledger = None
    success = not errors and ledger is not None
    return PortfolioValidationLedgerV233Result(
        version=VERSION, created_at=created_at, ledger_result_id=str(uuid.uuid4()),
        result_status="RECORDED_IN_MEMORY" if success else "BLOCKED",
        source_update_result_id=getattr(source, "update_result_id", None),
        source_portfolio_hash=source_hash,
        ledger_id=ledger.ledger_id if ledger else None,
        ledger_hash=ledger.ledger_hash if ledger else None,
        entry_recorded=success, policy_checks_passed=not validate_policy(policy),
        source_checks_passed=not source_errors,
        accounting_checks_passed=not accounting_errors,
        source_unchanged_checks_passed=unchanged,
        ledger_checks_passed=not ledger_errors,
        safety_checks_passed=success, all_checks_passed=success,
        funds_reserved=False, holdings_reserved=False, execution_blocked=True,
        transmit=False, credentials_used=False, market_data_api_called=False,
        account_api_called=False, network_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, validation_policy=policy, ledger=ledger,
        reasons=errors,
    )


def save_portfolio_validation_result(
    result: PortfolioValidationLedgerV233Result,
    directory: Path | str = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / f"portfolio_validation_{result.ledger_result_id}.json"
    latest = directory / "latest_portfolio_validation_v23_3.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_portfolio_validation_result(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

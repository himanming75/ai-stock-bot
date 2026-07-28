import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_decision_gate import (
    SandboxRiskDecisionGateResult,
    SandboxRiskGateDecision,
    verify_gate_decision,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "trading_engine" / "sandbox_risk_decision_ledger"
REQUIRED_RECORD_TEXT = "RECORD IN MEMORY SANDBOX RISK DECISION"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SandboxRiskDecisionLedgerPolicy:
    required_source_version: str = "V14.8"
    required_source_status: str = "DECIDED_IN_MEMORY"
    required_decision_status: str = "DECIDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_RECORD_TEXT
    maximum_ledger_entries: int = 100
    require_same_operator: bool = True
    require_valid_decision: bool = True
    require_chronological_order: bool = True
    reject_duplicate_decision_id: bool = True
    verify_hash_chain: bool = True
    ledger_recording_only: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxRiskDecisionLedgerEntry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    gate_result_id: str
    gate_decision_id: str
    gate_decision_hash: str
    assessment_id: str
    session_id: str
    operator: str
    source_risk_status: str
    source_risk_action: str
    gate_action: str
    manual_review_required: bool
    sandbox_progress_allowed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SandboxRiskDecisionLedgerResult:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    result_status_label: str
    latest_entry_id: str | None
    latest_entry_hash: str | None
    latest_decision_id: str | None
    latest_gate_action: str
    total_entry_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    decision_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    existing_ledger_checks_passed: bool
    hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    ledger_entry_recorded: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    ledger_policy: SandboxRiskDecisionLedgerPolicy
    entries: tuple[SandboxRiskDecisionLedgerEntry, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxRiskDecisionLedgerPolicy) -> list[str]:
    if not isinstance(policy, SandboxRiskDecisionLedgerPolicy):
        return ["Risk Decision Ledger Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.8",
        "required_source_status": "DECIDED_IN_MEMORY",
        "required_decision_status": "DECIDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_RECORD_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.9 기준과 다릅니다.")
    if policy.maximum_ledger_entries <= 0:
        errors.append("Ledger 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator", "require_valid_decision",
        "require_chronological_order", "reject_duplicate_decision_id",
        "verify_hash_chain", "ledger_recording_only", "credentials_forbidden",
        "market_data_api_disabled", "account_access_disabled",
        "network_access_disabled", "broker_api_disabled",
        "order_submission_disabled", "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.9에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxRiskGateDecision | None, list[str]]:
    if not isinstance(source, SandboxRiskDecisionGateResult):
        return None, ["Source는 V14.8 Risk Decision Gate Result여야 합니다."]
    errors: list[str] = []
    if not (
        source.version == "V14.8"
        and source.result_status == "DECIDED_IN_MEMORY"
        and source.all_checks_passed
        and source.gate_decision_completed
        and source.decision is not None
    ):
        errors.append("정상 V14.8 Gate Source가 아닙니다.")
    if any((
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
    )):
        errors.append("V14.8 Source 실행 안전장치가 올바르지 않습니다.")
    decision = source.decision
    if decision is not None:
        valid, decision_errors = verify_gate_decision(decision)
        if not valid:
            errors.extend(decision_errors)
        if source.decision_id != decision.gate_decision_id:
            errors.append("Gate Decision ID 연결이 다릅니다.")
        if source.decision_hash != decision.decision_hash:
            errors.append("Gate Decision Hash 연결이 다릅니다.")
        if source.gate_action != decision.gate_action:
            errors.append("Gate Action 연결이 다릅니다.")
    return decision, errors


def normalize_entries(existing: Any) -> tuple[SandboxRiskDecisionLedgerEntry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Entries는 tuple 또는 list여야 합니다.")
    if not all(isinstance(x, SandboxRiskDecisionLedgerEntry) for x in existing):
        raise TypeError("Existing Ledger Entry 형식이 올바르지 않습니다.")
    return tuple(existing)


def verify_ledger_chain(
    entries: tuple[SandboxRiskDecisionLedgerEntry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    decision_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            errors.append(f"Sequence {expected_sequence}가 올바르지 않습니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"Sequence {entry.sequence}의 Previous Hash가 다릅니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"Sequence {entry.sequence}의 Entry Hash가 다릅니다.")
        if entry.gate_decision_id in decision_ids:
            errors.append(f"중복 Gate Decision ID가 있습니다: {entry.gate_decision_id}")
        decision_ids.add(entry.gate_decision_id)
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            if previous_time and recorded_at < previous_time:
                errors.append("Ledger 기록 시간이 역순입니다.")
            previous_time = recorded_at
        except (TypeError, ValueError):
            errors.append("Ledger 기록 시간이 올바르지 않습니다.")
        if entry.gate_action not in {"PROCEED", "REVIEW", "PAUSE", "BLOCK"}:
            errors.append("Ledger Gate Action이 올바르지 않습니다.")
        if any((
            entry.paper_execution_authorized,
            entry.automatic_execution_authorized,
            not entry.execution_blocked,
            entry.credentials_used,
            entry.market_data_api_called,
            entry.network_accessed,
            entry.account_accessed,
            entry.broker_api_called,
            entry.order_submitted,
            entry.live_execution_authorized,
        )):
            errors.append("Ledger Entry 실행 안전장치가 올바르지 않습니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def _result(
    gate_policy: SandboxRiskDecisionLedgerPolicy,
    now: datetime,
    status: str,
    entries: tuple[SandboxRiskDecisionLedgerEntry, ...],
    reasons: list[str],
    **checks: bool,
) -> SandboxRiskDecisionLedgerResult:
    latest = entries[-1] if entries else None
    return SandboxRiskDecisionLedgerResult(
        version="V14.9", created_at=now.isoformat(),
        ledger_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label=(
            "Risk Decision Ledger 기록 완료" if status == "RECORDED_IN_MEMORY"
            else "Ledger 차단" if status == "BLOCKED" else "Ledger 실패"
        ),
        latest_entry_id=latest.ledger_entry_id if latest else None,
        latest_entry_hash=latest.entry_hash if latest else None,
        latest_decision_id=latest.gate_decision_id if latest else None,
        latest_gate_action=latest.gate_action if latest else "BLOCK",
        total_entry_count=len(entries), records_trimmed=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        decision_checks_passed=checks.get("decision", False),
        operator_checks_passed=checks.get("operator", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        existing_ledger_checks_passed=checks.get("existing", False),
        hash_chain_checks_passed=checks.get("chain", False),
        safety_checks_passed=True,
        all_checks_passed=status == "RECORDED_IN_MEMORY",
        ledger_entry_recorded=status == "RECORDED_IN_MEMORY",
        paper_execution_authorized=False, automatic_execution_authorized=False,
        execution_blocked=True, credentials_used=False,
        market_data_api_called=False, network_accessed=False,
        account_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        ledger_policy=gate_policy, entries=entries, reasons=reasons,
        warnings=[
            "V14.9는 Gate 결정 기록만 하며 실제 주문 권한을 부여하지 않습니다.",
            "Broker API, 계좌, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Ledger Sequence와 SHA-256 Hash Chain을 확인합니다.",
            "다음 In-Memory Sandbox 단계로 진행합니다.",
        ],
    )


def record_sandbox_risk_decision(
    source: Any,
    operator: str,
    confirmation_text: str,
    existing: Any = None,
    policy: SandboxRiskDecisionLedgerPolicy | None = None,
    now: datetime | None = None,
) -> SandboxRiskDecisionLedgerResult:
    policy = policy or SandboxRiskDecisionLedgerPolicy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        return _result(
            policy, now, "BLOCKED", (), policy_errors + input_errors,
            policy=not policy_errors, input=not input_errors,
        )
    try:
        entries = normalize_entries(existing)
    except TypeError as error:
        return _result(policy, now, "BLOCKED", (), [str(error)], policy=True, input=True)
    chain_valid, chain_errors = verify_ledger_chain(entries)
    if not chain_valid:
        return _result(
            policy, now, "BLOCKED", entries, chain_errors,
            policy=True, input=True,
        )
    decision, source_errors = validate_source(source)
    if source_errors or decision is None:
        return _result(
            policy, now, "FAILED", entries, source_errors,
            policy=True, input=True, existing=True, chain=True,
        )
    if operator != decision.operator:
        return _result(
            policy, now, "BLOCKED", entries,
            ["Operator가 V14.8 Gate Decision과 다릅니다."],
            policy=True, input=True, source=True, decision=True,
            existing=True, chain=True,
        )
    if any(x.gate_decision_id == decision.gate_decision_id for x in entries):
        return _result(
            policy, now, "BLOCKED", entries,
            ["중복 Gate Decision ID가 차단되었습니다."],
            policy=True, input=True, source=True, decision=True,
            operator=True, existing=True, chain=True,
        )
    if entries and now < datetime.fromisoformat(entries[-1].recorded_at):
        return _result(
            policy, now, "BLOCKED", entries,
            ["역순 Ledger 기록 시간이 차단되었습니다."],
            policy=True, input=True, source=True, decision=True,
            operator=True, duplicate=True, existing=True, chain=True,
        )
    payload = {
        "ledger_entry_id": str(uuid.uuid4()),
        "sequence": len(entries) + 1,
        "recorded_at": now.isoformat(),
        "previous_entry_hash": entries[-1].entry_hash if entries else GENESIS_HASH,
        "gate_result_id": source.gate_result_id,
        "gate_decision_id": decision.gate_decision_id,
        "gate_decision_hash": decision.decision_hash,
        "assessment_id": decision.assessment_id,
        "session_id": decision.session_id,
        "operator": operator,
        "source_risk_status": decision.source_risk_status,
        "source_risk_action": decision.source_risk_action,
        "gate_action": decision.gate_action,
        "manual_review_required": decision.manual_review_required,
        "sandbox_progress_allowed": decision.sandbox_progress_allowed,
        "paper_execution_authorized": False,
        "automatic_execution_authorized": False,
        "execution_blocked": True,
        "credentials_used": False,
        "market_data_api_called": False,
        "network_accessed": False,
        "account_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    new_entry = SandboxRiskDecisionLedgerEntry(
        **payload, entry_hash=sha256_payload(payload)
    )
    combined = entries + (new_entry,)
    trimmed_count = max(0, len(combined) - policy.maximum_ledger_entries)
    if trimmed_count:
        kept = combined[-policy.maximum_ledger_entries:]
        rebuilt: list[SandboxRiskDecisionLedgerEntry] = []
        previous_hash = GENESIS_HASH
        for sequence, item in enumerate(kept, start=1):
            item_payload = item.payload_without_hash()
            item_payload.update(sequence=sequence, previous_entry_hash=previous_hash)
            item = SandboxRiskDecisionLedgerEntry(
                **item_payload, entry_hash=sha256_payload(item_payload)
            )
            rebuilt.append(item)
            previous_hash = item.entry_hash
        combined = tuple(rebuilt)
    valid, errors = verify_ledger_chain(combined)
    result = _result(
        policy, now, "RECORDED_IN_MEMORY" if valid else "FAILED",
        combined, [
            f"Gate Action {decision.gate_action} 결정이 Ledger에 기록되었습니다.",
            f"현재 Ledger Entry는 {len(combined)}개입니다.",
        ] + errors,
        policy=True, input=True, source=True, decision=True,
        operator=True, duplicate=True, chronology=True,
        existing=True, chain=valid,
    )
    result.records_trimmed = trimmed_count
    return result


def save_ledger_result(
    result: SandboxRiskDecisionLedgerResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report = output_directory / f"sandbox_risk_decision_ledger_{stamp}.json"
    latest = output_directory / "latest_sandbox_risk_decision_ledger.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_ledger_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

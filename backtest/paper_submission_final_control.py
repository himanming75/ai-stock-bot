import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_submission_reconciliation import (
    PaperSubmissionReconciliationResult,
    verify_reconciliation_report,
)
from backtest.paper_submission_release_gate import (
    PaperSubmissionReleaseResult,
    verify_release,
)
from backtest.paper_submission_release_ledger import (
    PaperSubmissionReleaseLedgerResult,
    verify_ledger_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_submission_final_control"
)
REQUIRED_CONTROL_TEXT = "PASS PAPER SUBMISSION FINAL CONTROL"


@dataclass(frozen=True)
class PaperSubmissionFinalControlPolicy:
    required_reconciliation_version: str = "V13.6"
    required_release_version: str = "V13.7"
    required_ledger_version: str = "V13.8"
    required_confirmation_text: str = REQUIRED_CONTROL_TEXT
    maximum_control_records: int = 100
    require_same_operator: bool = True
    require_source_hashes: bool = True
    require_exact_identity_link: bool = True
    require_chronological_order: bool = True
    reject_duplicate_release_id: bool = True
    final_control_only: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperSubmissionFinalControlSeal:
    control_id: str
    controlled_at: str
    control_status: str
    reconciliation_result_id: str
    reconciliation_id: str
    reconciliation_report_hash: str
    release_result_id: str
    release_id: str
    release_hash: str
    ledger_result_id: str
    ledger_entry_id: str
    ledger_entry_hash: str
    translation_batch_id: str
    submission_batch_id: str
    operator: str
    controlled_item_count: int
    paper_submission_controlled: bool
    paper_execution_authorized: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    control_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("control_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperSubmissionFinalControlResult:
    version: str
    created_at: str
    control_result_id: str
    result_status: str
    result_status_label: str
    latest_control_id: str | None
    latest_control_hash: str | None
    controlled_item_count: int
    total_control_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    reconciliation_checks_passed: bool
    release_checks_passed: bool
    ledger_checks_passed: bool
    linkage_checks_passed: bool
    chronology_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_control_checks_passed: bool
    seal_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    final_control_passed: bool
    paper_submission_controlled: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    control_policy: PaperSubmissionFinalControlPolicy
    controls: tuple[PaperSubmissionFinalControlSeal, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["control_policy"] = self.control_policy.to_dict()
        payload["controls"] = [item.to_dict() for item in self.controls]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperSubmissionFinalControlPolicy) -> list[str]:
    if not isinstance(policy, PaperSubmissionFinalControlPolicy):
        return ["Final Control Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_reconciliation_version": "V13.6",
        "required_release_version": "V13.7",
        "required_ledger_version": "V13.8",
        "required_confirmation_text": REQUIRED_CONTROL_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V13.9 기준과 다릅니다.")
    if policy.maximum_control_records <= 0:
        errors.append("Control 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator",
        "require_source_hashes",
        "require_exact_identity_link",
        "require_chronological_order",
        "reject_duplicate_release_id",
        "final_control_only",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V13.9에서 True여야 합니다.")
    return errors


def source_is_safe(source: Any) -> bool:
    return bool(
        source.paper_execution_authorized is False
        and source.automatic_execution_authorized is False
        and source.execution_blocked is True
        and source.network_accessed is False
        and source.account_accessed is False
        and source.broker_api_called is False
        and source.broker_order_created is False
        and source.order_submitted is False
        and source.live_order_created is False
        and source.live_execution_authorized is False
    )


def validate_sources(
    reconciliation: Any,
    release_result: Any,
    ledger_result: Any,
    checked_at: datetime,
) -> tuple[Any, Any, Any, list[str], list[str], list[str]]:
    reconciliation_errors: list[str] = []
    release_errors: list[str] = []
    ledger_errors: list[str] = []
    report = None
    release = None
    entry = None
    if not isinstance(reconciliation, PaperSubmissionReconciliationResult):
        reconciliation_errors.append("V13.6 Reconciliation Result가 아닙니다.")
    else:
        if not (
            reconciliation.version == "V13.6"
            and reconciliation.result_status == "RECONCILED"
            and reconciliation.all_checks_passed
            and reconciliation.reconciliation_completed
            and source_is_safe(reconciliation)
            and reconciliation.report is not None
        ):
            reconciliation_errors.append("정상 V13.6 Reconciliation Source가 아닙니다.")
        else:
            report = reconciliation.report
            valid, errors = verify_reconciliation_report(report)
            if not valid:
                reconciliation_errors.extend(errors)
    if not isinstance(release_result, PaperSubmissionReleaseResult):
        release_errors.append("V13.7 Release Result가 아닙니다.")
    else:
        if not (
            release_result.version == "V13.7"
            and release_result.result_status == "PAPER_RELEASED"
            and release_result.all_checks_passed
            and release_result.paper_submission_released
            and source_is_safe(release_result)
            and release_result.releases
        ):
            release_errors.append("정상 V13.7 Release Source가 아닙니다.")
        else:
            release = release_result.releases[-1]
            valid, time_valid, errors = verify_release(release, checked_at)
            if not valid or not time_valid:
                release_errors.extend(errors)
    if not isinstance(ledger_result, PaperSubmissionReleaseLedgerResult):
        ledger_errors.append("V13.8 Ledger Result가 아닙니다.")
    else:
        if not (
            ledger_result.version == "V13.8"
            and ledger_result.result_status == "RECORDED"
            and ledger_result.all_checks_passed
            and ledger_result.ledger_entry_recorded
            and source_is_safe(ledger_result)
            and ledger_result.entries
        ):
            ledger_errors.append("정상 V13.8 Ledger Source가 아닙니다.")
        else:
            valid, errors = verify_ledger_chain(ledger_result.entries)
            if not valid:
                ledger_errors.extend(errors)
            entry = ledger_result.entries[-1]
    return (
        report, release, entry,
        reconciliation_errors, release_errors, ledger_errors,
    )


def normalize_controls(existing: Any) -> tuple[PaperSubmissionFinalControlSeal, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Controls는 tuple 또는 list여야 합니다.")
    controls: list[PaperSubmissionFinalControlSeal] = []
    for item in existing:
        if not isinstance(item, PaperSubmissionFinalControlSeal):
            raise TypeError("Existing Control 형식이 올바르지 않습니다.")
        controls.append(item)
    return tuple(controls)


def verify_control_seal(
    seal: PaperSubmissionFinalControlSeal,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if seal.control_status != "FINAL_CONTROL_PASSED":
        errors.append("Control 상태가 FINAL_CONTROL_PASSED가 아닙니다.")
    if not seal.paper_submission_controlled or seal.controlled_item_count <= 0:
        errors.append("Control Item 정보가 올바르지 않습니다.")
    if any((
        seal.paper_execution_authorized,
        seal.network_accessed,
        seal.broker_api_called,
        seal.broker_order_created,
        seal.order_submitted,
        seal.live_execution_authorized,
    )):
        errors.append("Control Seal에 실제 실행 흔적이 있습니다.")
    if seal.control_hash != sha256_payload(seal.payload_without_hash()):
        errors.append("Final Control Hash가 일치하지 않습니다.")
    return not errors, errors


def run_paper_submission_final_control(
    reconciliation: PaperSubmissionReconciliationResult,
    release_result: PaperSubmissionReleaseResult,
    ledger_result: PaperSubmissionReleaseLedgerResult,
    operator: str,
    confirmation_text: str,
    existing_controls: Any = None,
    policy: PaperSubmissionFinalControlPolicy | None = None,
    now: datetime | None = None,
) -> PaperSubmissionFinalControlResult:
    policy = policy or PaperSubmissionFinalControlPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Final Control 확인 문구가 일치하지 않습니다.")
    (
        report, release, entry,
        reconciliation_errors, release_errors, ledger_errors,
    ) = validate_sources(reconciliation, release_result, ledger_result, now)
    linkage_errors: list[str] = []
    operator_errors: list[str] = []
    chronology_errors: list[str] = []
    if report and release and entry:
        if not (
            release.reconciliation_id == report.reconciliation_id
            and release.reconciliation_report_hash == report.report_hash
            and release.translation_batch_id == report.translation_batch_id
            and release.submission_batch_id == report.submission_batch_id
            and entry.release_result_id == release_result.release_result_id
            and entry.release_id == release.release_id
            and entry.release_hash == release.release_hash
            and entry.reconciliation_id == report.reconciliation_id
            and entry.submission_batch_id == report.submission_batch_id
        ):
            linkage_errors.append("V13.6~V13.8 Source ID 또는 Hash 연결이 다릅니다.")
        if not (
            report.operator == release.operator == entry.operator == clean_operator
        ):
            operator_errors.append("세 Source와 Control Operator가 일치하지 않습니다.")
        try:
            report_time = datetime.fromisoformat(report.created_at)
            release_time = datetime.fromisoformat(release.released_at)
            ledger_time = datetime.fromisoformat(entry.recorded_at)
            if not report_time <= release_time <= ledger_time <= now:
                chronology_errors.append("Source 시간 순서가 올바르지 않습니다.")
        except (TypeError, ValueError):
            chronology_errors.append("Source 시간 형식이 올바르지 않습니다.")
    existing_errors: list[str] = []
    try:
        existing = normalize_controls(existing_controls)
    except (TypeError, ValueError) as error:
        existing = ()
        existing_errors.append(str(error))
    for control in existing:
        valid, errors = verify_control_seal(control)
        if not valid:
            existing_errors.extend(errors)
    duplicate_errors: list[str] = []
    if release and any(item.release_id == release.release_id for item in existing):
        duplicate_errors.append("동일 Release의 Final Control이 이미 존재합니다.")
    seal: PaperSubmissionFinalControlSeal | None = None
    seal_errors: list[str] = []
    preliminary_errors = (
        policy_errors + input_errors + reconciliation_errors
        + release_errors + ledger_errors + linkage_errors
        + chronology_errors + operator_errors + existing_errors
        + duplicate_errors
    )
    if not preliminary_errors and report and release and entry:
        draft = PaperSubmissionFinalControlSeal(
            control_id=str(uuid.uuid4()),
            controlled_at=created_at,
            control_status="FINAL_CONTROL_PASSED",
            reconciliation_result_id=reconciliation.reconciliation_result_id,
            reconciliation_id=report.reconciliation_id,
            reconciliation_report_hash=report.report_hash,
            release_result_id=release_result.release_result_id,
            release_id=release.release_id,
            release_hash=release.release_hash,
            ledger_result_id=ledger_result.ledger_result_id,
            ledger_entry_id=entry.ledger_entry_id,
            ledger_entry_hash=entry.entry_hash,
            translation_batch_id=report.translation_batch_id,
            submission_batch_id=report.submission_batch_id,
            operator=clean_operator,
            controlled_item_count=report.reconciled_count,
            paper_submission_controlled=True,
            paper_execution_authorized=False,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            control_hash="",
        )
        seal = PaperSubmissionFinalControlSeal(
            **{
                **asdict(draft),
                "control_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, errors = verify_control_seal(seal)
        if not valid:
            seal_errors.extend(errors)
    controls = (*existing, *((seal,) if seal else ()))
    trimmed = max(0, len(controls) - policy.maximum_control_records)
    if trimmed:
        controls = controls[-policy.maximum_control_records:]
    all_errors = preliminary_errors + seal_errors
    passed = bool(seal) and not all_errors
    sources_valid = not (
        reconciliation_errors or release_errors or ledger_errors
    )
    status = "FINAL_CONTROL_PASSED" if passed else (
        "BLOCKED" if sources_valid else "FAILED"
    )
    return PaperSubmissionFinalControlResult(
        version="V13.9",
        created_at=created_at,
        control_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "FINAL_CONTROL_PASSED": "Paper Submission 최종 통제 통과",
            "BLOCKED": "Final Control 연결 또는 입력 차단",
            "FAILED": "V13.6~V13.8 Source 검증 실패",
        }[status],
        latest_control_id=seal.control_id if seal else None,
        latest_control_hash=seal.control_hash if seal else None,
        controlled_item_count=seal.controlled_item_count if seal else 0,
        total_control_count=len(controls),
        records_trimmed=trimmed,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        reconciliation_checks_passed=not reconciliation_errors,
        release_checks_passed=not release_errors,
        ledger_checks_passed=not ledger_errors,
        linkage_checks_passed=not linkage_errors,
        chronology_checks_passed=not chronology_errors,
        operator_checks_passed=not operator_errors,
        duplicate_checks_passed=not duplicate_errors,
        existing_control_checks_passed=not existing_errors,
        seal_checks_passed=bool(seal) and not seal_errors,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        final_control_passed=passed,
        paper_submission_controlled=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        control_policy=policy,
        controls=controls,
        reasons=[
            "V13.6~V13.8 연결과 안전 조건이 최종 통제를 통과했습니다."
            if passed else "Paper Submission Final Control이 차단되었습니다."
        ],
        warnings=all_errors + [
            "FINAL_CONTROL_PASSED는 실제 Broker 주문 제출 권한이 아닙니다."
        ],
        next_actions=[
            "Control Seal의 ID, Hash 및 연결 Source를 수동 검토합니다.",
            "Broker API 또는 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_final_control_result(
    result: PaperSubmissionFinalControlResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_submission_final_control_{stamp}.json"
    latest = directory / "latest_paper_submission_final_control.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_final_control_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.9":
        raise ValueError("V13.9 결과 파일이 아닙니다.")
    for item in payload.get("controls", []):
        seal = PaperSubmissionFinalControlSeal(**item)
        valid, errors = verify_control_seal(seal)
        if not valid:
            raise ValueError("저장된 Final Control이 올바르지 않습니다: " + "; ".join(errors))
    return payload

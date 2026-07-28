import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.paper_submission_reconciliation import (
    PaperSubmissionReconciliationReport,
    PaperSubmissionReconciliationResult,
    verify_reconciliation_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_submission_release_gate"
)
REQUIRED_RELEASE_TEXT = "RELEASE RECONCILED PAPER SUBMISSION"


@dataclass(frozen=True)
class PaperSubmissionReleasePolicy:
    required_source_version: str = "V13.6"
    required_source_status: str = "RECONCILED"
    required_report_status: str = "RECONCILED"
    required_confirmation_text: str = REQUIRED_RELEASE_TEXT
    release_validity_minutes: int = 10
    maximum_release_records: int = 100
    require_same_operator: bool = True
    require_source_hash: bool = True
    require_all_items_reconciled: bool = True
    reject_duplicate_reconciliation: bool = True
    paper_preparation_only: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperSubmissionRelease:
    release_id: str
    released_at: str
    expires_at: str
    release_status: str
    reconciliation_result_id: str
    reconciliation_id: str
    reconciliation_report_hash: str
    translation_batch_id: str
    submission_batch_id: str
    operator: str
    released_item_count: int
    paper_submission_released: bool
    paper_execution_authorized: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    release_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("release_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperSubmissionReleaseResult:
    version: str
    created_at: str
    release_result_id: str
    result_status: str
    result_status_label: str
    latest_release_id: str | None
    latest_expires_at: str | None
    total_release_count: int
    valid_release_count: int
    released_item_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    report_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_release_checks_passed: bool
    issued_release_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    paper_submission_released: bool
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
    release_policy: PaperSubmissionReleasePolicy
    releases: tuple[PaperSubmissionRelease, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["release_policy"] = self.release_policy.to_dict()
        payload["releases"] = [item.to_dict() for item in self.releases]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperSubmissionReleasePolicy) -> list[str]:
    if not isinstance(policy, PaperSubmissionReleasePolicy):
        return ["Release Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V13.6",
        "required_source_status": "RECONCILED",
        "required_report_status": "RECONCILED",
        "required_confirmation_text": REQUIRED_RELEASE_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V13.7 기준과 다릅니다.")
    if policy.release_validity_minutes <= 0:
        errors.append("Release 유효시간은 0보다 커야 합니다.")
    if policy.maximum_release_records <= 0:
        errors.append("Release 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator",
        "require_source_hash",
        "require_all_items_reconciled",
        "reject_duplicate_reconciliation",
        "paper_preparation_only",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V13.7에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[
    PaperSubmissionReconciliationReport | None,
    list[str],
    list[str],
]:
    source_errors: list[str] = []
    report_errors: list[str] = []
    report: PaperSubmissionReconciliationReport | None = None
    if not isinstance(source, PaperSubmissionReconciliationResult):
        source_errors.append("Source는 V13.6 Reconciliation Result여야 합니다.")
        return None, source_errors, report_errors
    if source.version != "V13.6":
        source_errors.append("Source Version이 V13.6이 아닙니다.")
    if source.result_status != "RECONCILED":
        source_errors.append("Source가 RECONCILED 상태가 아닙니다.")
    if not source.all_checks_passed or not source.reconciliation_completed:
        source_errors.append("Source 검사가 완료되지 않았습니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.network_accessed,
        source.account_accessed,
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        source_errors.append("Source 실행 안전장치가 올바르지 않습니다.")
    if not isinstance(source.report, PaperSubmissionReconciliationReport):
        report_errors.append("Reconciliation Report가 없습니다.")
    else:
        report = source.report
        valid, errors = verify_reconciliation_report(report)
        if not valid:
            report_errors.extend(errors)
        if source.reconciliation_id != report.reconciliation_id:
            report_errors.append("Reconciliation ID 연결이 다릅니다.")
        if source.report_hash != report.report_hash:
            report_errors.append("Reconciliation Report Hash 연결이 다릅니다.")
        if source.reconciled_count != report.reconciled_count:
            report_errors.append("Reconciled Count 연결이 다릅니다.")
    return report, source_errors, report_errors


def normalize_releases(existing: Any) -> tuple[PaperSubmissionRelease, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Releases는 tuple 또는 list여야 합니다.")
    values: list[PaperSubmissionRelease] = []
    for item in existing:
        if not isinstance(item, PaperSubmissionRelease):
            raise TypeError("Existing Release 형식이 올바르지 않습니다.")
        values.append(item)
    return tuple(values)


def verify_release(
    release: PaperSubmissionRelease,
    checked_at: datetime | None = None,
) -> tuple[bool, bool, list[str]]:
    checked_at = checked_at or datetime.now().astimezone()
    errors: list[str] = []
    if release.release_status != "PAPER_RELEASED":
        errors.append("Release 상태가 PAPER_RELEASED가 아닙니다.")
    if not release.paper_submission_released:
        errors.append("Paper Submission Release가 설정되지 않았습니다.")
    if release.released_item_count <= 0:
        errors.append("Release Item이 없습니다.")
    if any((
        release.paper_execution_authorized,
        release.network_accessed,
        release.broker_api_called,
        release.broker_order_created,
        release.order_submitted,
        release.live_execution_authorized,
    )):
        errors.append("Release에 실제 실행 흔적이 있습니다.")
    if release.release_hash != sha256_payload(release.payload_without_hash()):
        errors.append("Release Hash가 일치하지 않습니다.")
    try:
        expiry = datetime.fromisoformat(release.expires_at)
        time_valid = checked_at <= expiry
    except (TypeError, ValueError):
        time_valid = False
    if not time_valid:
        errors.append("Release가 만료되었습니다.")
    return not errors, time_valid, errors


def release_paper_submission(
    source: PaperSubmissionReconciliationResult,
    operator: str,
    confirmation_text: str,
    existing_releases: Any = None,
    policy: PaperSubmissionReleasePolicy | None = None,
    now: datetime | None = None,
) -> PaperSubmissionReleaseResult:
    policy = policy or PaperSubmissionReleasePolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Release 확인 문구가 일치하지 않습니다.")
    report, source_errors, report_errors = validate_source(source)
    operator_errors: list[str] = []
    if report and policy.require_same_operator and report.operator != clean_operator:
        operator_errors.append("Source Operator와 Release Operator가 다릅니다.")
    existing_errors: list[str] = []
    try:
        existing = normalize_releases(existing_releases)
    except (TypeError, ValueError) as error:
        existing = ()
        existing_errors.append(str(error))
    for item in existing:
        valid, _, errors = verify_release(item, now)
        if not valid:
            existing_errors.extend(errors)
    duplicate_errors: list[str] = []
    if report and any(
        item.reconciliation_id == report.reconciliation_id for item in existing
    ):
        duplicate_errors.append("동일 Reconciliation의 중복 Release입니다.")
    release: PaperSubmissionRelease | None = None
    issue_errors: list[str] = []
    preliminary_errors = (
        policy_errors + input_errors + source_errors + report_errors
        + operator_errors + existing_errors + duplicate_errors
    )
    if not preliminary_errors and report:
        draft = PaperSubmissionRelease(
            release_id=str(uuid.uuid4()),
            released_at=created_at,
            expires_at=(
                now + timedelta(minutes=policy.release_validity_minutes)
            ).isoformat(),
            release_status="PAPER_RELEASED",
            reconciliation_result_id=source.reconciliation_result_id,
            reconciliation_id=report.reconciliation_id,
            reconciliation_report_hash=report.report_hash,
            translation_batch_id=report.translation_batch_id,
            submission_batch_id=report.submission_batch_id,
            operator=clean_operator,
            released_item_count=report.reconciled_count,
            paper_submission_released=True,
            paper_execution_authorized=False,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            release_hash="",
        )
        release = PaperSubmissionRelease(
            **{
                **asdict(draft),
                "release_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, _, errors = verify_release(release, now)
        if not valid:
            issue_errors.extend(errors)
    releases = (*existing, *((release,) if release else ()))
    trimmed = max(0, len(releases) - policy.maximum_release_records)
    if trimmed:
        releases = releases[-policy.maximum_release_records:]
    all_errors = preliminary_errors + issue_errors
    passed = bool(release) and not all_errors
    source_valid = not source_errors and not report_errors
    status = "PAPER_RELEASED" if passed else (
        "BLOCKED" if source_valid else "FAILED"
    )
    valid_count = sum(verify_release(item, now)[0] for item in releases)
    return PaperSubmissionReleaseResult(
        version="V13.7",
        created_at=created_at,
        release_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "PAPER_RELEASED": "Paper Submission 수동 Release 완료",
            "BLOCKED": "Paper Submission Release 차단",
            "FAILED": "V13.6 Source 검증 실패",
        }[status],
        latest_release_id=release.release_id if release else None,
        latest_expires_at=release.expires_at if release else None,
        total_release_count=len(releases),
        valid_release_count=valid_count,
        released_item_count=release.released_item_count if release else 0,
        records_trimmed=trimmed,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        report_checks_passed=not report_errors,
        operator_checks_passed=not operator_errors,
        duplicate_checks_passed=not duplicate_errors,
        existing_release_checks_passed=not existing_errors,
        issued_release_checks_passed=bool(release) and not issue_errors,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        paper_submission_released=passed,
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
        release_policy=policy,
        releases=releases,
        reasons=[
            "대조 완료된 Paper Submission을 다음 준비 단계로 Release했습니다."
            if passed else "Paper Submission Release가 차단되었습니다."
        ],
        warnings=all_errors + [
            "PAPER_RELEASED는 실제 Broker 주문 제출 권한이 아닙니다."
        ],
        next_actions=[
            "Release Hash와 만료시간을 수동 확인합니다.",
            "Broker API 또는 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_release_result(
    result: PaperSubmissionReleaseResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_submission_release_{stamp}.json"
    latest = directory / "latest_paper_submission_release.json"
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


def load_release_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.7":
        raise ValueError("V13.7 결과 파일이 아닙니다.")
    for release in payload.get("releases", []):
        saved_hash = release.get("release_hash")
        hash_payload = dict(release)
        hash_payload.pop("release_hash", None)
        if saved_hash != sha256_payload(hash_payload):
            raise ValueError("저장된 Release Hash가 일치하지 않습니다.")
    return payload

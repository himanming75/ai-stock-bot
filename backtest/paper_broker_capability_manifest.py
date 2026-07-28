import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_connection_dry_run_validator import (
    PaperConnectionDryRunCertificate,
    PaperConnectionDryRunResult,
    verify_dry_run_certificate,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_broker_capability_manifest"
)
REQUIRED_MANIFEST_TEXT = "BUILD PAPER BROKER CAPABILITY MANIFEST"
SAFE_ORDER_TYPES = ("MARKET", "LIMIT")
SAFE_ACTIONS = ("BUY", "SELL")
SAFE_TIME_IN_FORCE = ("DAY",)
BLOCKED_CAPABILITIES = (
    "LIVE_TRADING", "SHORT_SELLING", "MARGIN", "OPTIONS", "FUTURES",
    "CRYPTO", "STOP_ORDER", "TRAILING_STOP", "AFTER_HOURS",
    "AUTOMATIC_SUBMISSION",
)


@dataclass(frozen=True)
class PaperBrokerCapabilityPolicy:
    required_source_version: str = "V13.2"
    required_source_status: str = "VALIDATED"
    required_confirmation_text: str = REQUIRED_MANIFEST_TEXT
    broker_profile: str = "GENERIC_PAPER"
    environment: str = "PAPER"
    supported_order_types: tuple[str, ...] = SAFE_ORDER_TYPES
    supported_actions: tuple[str, ...] = SAFE_ACTIONS
    supported_time_in_force: tuple[str, ...] = SAFE_TIME_IN_FORCE
    blocked_capabilities: tuple[str, ...] = BLOCKED_CAPABILITIES
    require_same_operator: bool = True
    require_source_hash: bool = True
    connection_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerCapabilityManifest:
    manifest_id: str
    created_at: str
    manifest_status: str
    broker_profile: str
    environment: str
    operator: str
    dry_run_certificate_id: str
    dry_run_certificate_hash: str
    supported_order_types: tuple[str, ...]
    supported_actions: tuple[str, ...]
    supported_time_in_force: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    paper_mapping_supported: bool
    capability_review_completed: bool
    connection_authorized: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    manifest_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("manifest_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperBrokerCapabilityManifestResult:
    version: str
    created_at: str
    manifest_result_id: str
    result_status: str
    result_status_label: str
    manifest_id: str | None
    manifest_hash: str | None
    supported_capability_count: int
    blocked_capability_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    capability_checks_passed: bool
    manifest_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    capability_manifest_created: bool
    connection_authorized: bool
    paper_session_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    session_opened: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    capability_policy: PaperBrokerCapabilityPolicy
    manifest: PaperBrokerCapabilityManifest | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capability_policy"] = self.capability_policy.to_dict()
        payload["manifest"] = self.manifest.to_dict() if self.manifest else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def calculate_manifest_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperBrokerCapabilityPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_source_version != "V13.2":
        errors.append("Source Version은 V13.2여야 합니다.")
    if policy.environment != "PAPER":
        errors.append("PAPER 환경만 허용됩니다.")
    if policy.supported_order_types != SAFE_ORDER_TYPES:
        errors.append("지원 Order Type 범위가 안전 기준과 다릅니다.")
    if policy.supported_actions != SAFE_ACTIONS:
        errors.append("지원 Action 범위가 안전 기준과 다릅니다.")
    if policy.supported_time_in_force != SAFE_TIME_IN_FORCE:
        errors.append("지원 Time-In-Force 범위가 안전 기준과 다릅니다.")
    if set(policy.blocked_capabilities) != set(BLOCKED_CAPABILITIES):
        errors.append("필수 차단 Capability 목록이 다릅니다.")
    if not (
        policy.connection_disabled and policy.broker_api_disabled
        and policy.order_submission_disabled and policy.live_execution_disabled
    ):
        errors.append("연결 및 실행 차단 정책이 필요합니다.")
    return errors


def validate_source(
    source: PaperConnectionDryRunResult,
    operator: str,
    policy: PaperBrokerCapabilityPolicy,
) -> tuple[PaperConnectionDryRunCertificate | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperConnectionDryRunResult):
        return None, ["V13.2 Dry-Run Result 형식이 아닙니다."]
    if source.version != policy.required_source_version:
        errors.append("V13.2 Source가 아닙니다.")
    if source.result_status != policy.required_source_status:
        errors.append("VALIDATED Source가 아닙니다.")
    certificate = source.certificate
    if certificate is None:
        errors.append("Dry-Run Certificate가 없습니다.")
        return None, errors
    valid, verify_errors = verify_dry_run_certificate(certificate)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.connection_dry_run_validated:
        errors.append("검증 완료된 Dry-Run Source가 아닙니다.")
    if source.connection_authorized or source.broker_api_called:
        errors.append("연결 또는 Broker 호출 흔적이 있습니다.")
    if policy.require_same_operator and certificate.operator != operator:
        errors.append("Operator가 Source와 일치하지 않습니다.")
    return certificate, errors


def verify_capability_manifest(
    manifest: PaperBrokerCapabilityManifest,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if manifest.manifest_status != "DECLARED":
        errors.append("Manifest가 DECLARED 상태가 아닙니다.")
    if manifest.environment != "PAPER":
        errors.append("Manifest 환경이 PAPER가 아닙니다.")
    if manifest.supported_order_types != SAFE_ORDER_TYPES:
        errors.append("지원 Order Type이 안전 범위를 벗어났습니다.")
    if manifest.supported_actions != SAFE_ACTIONS:
        errors.append("지원 Action이 안전 범위를 벗어났습니다.")
    if set(manifest.blocked_capabilities) != set(BLOCKED_CAPABILITIES):
        errors.append("차단 Capability가 누락되었습니다.")
    if any(
        (
            manifest.connection_authorized,
            manifest.broker_api_called,
            manifest.order_submitted,
            manifest.live_execution_authorized,
        )
    ):
        errors.append("Manifest에 연결 또는 실행 권한이 있습니다.")
    expected = calculate_manifest_hash(manifest.payload_without_hash())
    if expected != manifest.manifest_hash:
        errors.append("Manifest Hash가 일치하지 않습니다.")
    return not errors, errors


def build_paper_broker_capability_manifest(
    source: PaperConnectionDryRunResult,
    operator: str,
    confirmation_text: str,
    policy: PaperBrokerCapabilityPolicy | None = None,
    now: datetime | None = None,
) -> PaperBrokerCapabilityManifestResult:
    policy = policy or PaperBrokerCapabilityPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    certificate, source_errors = validate_source(source, clean_operator, policy)
    manifest: PaperBrokerCapabilityManifest | None = None
    hash_ok = False
    capability_ok = not policy_errors
    all_errors = policy_errors + input_errors + source_errors
    if not all_errors and certificate is not None:
        draft = PaperBrokerCapabilityManifest(
            manifest_id=str(uuid.uuid4()),
            created_at=created_at,
            manifest_status="DECLARED",
            broker_profile=policy.broker_profile,
            environment=policy.environment,
            operator=clean_operator,
            dry_run_certificate_id=certificate.certificate_id,
            dry_run_certificate_hash=certificate.certificate_hash,
            supported_order_types=policy.supported_order_types,
            supported_actions=policy.supported_actions,
            supported_time_in_force=policy.supported_time_in_force,
            blocked_capabilities=policy.blocked_capabilities,
            paper_mapping_supported=True,
            capability_review_completed=True,
            connection_authorized=False,
            broker_api_called=False,
            order_submitted=False,
            live_execution_authorized=False,
            manifest_hash="",
        )
        manifest = PaperBrokerCapabilityManifest(
            **{
                **asdict(draft),
                "manifest_hash": calculate_manifest_hash(
                    draft.payload_without_hash()
                ),
            }
        )
        hash_ok, hash_errors = verify_capability_manifest(manifest)
        all_errors.extend(hash_errors)
    safety_ok = (
        policy.connection_disabled and policy.broker_api_disabled
        and policy.order_submission_disabled and policy.live_execution_disabled
    )
    source_ok = not source_errors
    passed = (
        not policy_errors and not input_errors and source_ok
        and capability_ok and hash_ok and safety_ok and not all_errors
    )
    status = "DECLARED" if passed else ("BLOCKED" if source_ok else "FAILED")
    return PaperBrokerCapabilityManifestResult(
        version="V13.3",
        created_at=created_at,
        manifest_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "DECLARED": "Paper Capability 범위 선언 완료",
            "BLOCKED": "Capability 입력 또는 정책 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        manifest_id=manifest.manifest_id if manifest else None,
        manifest_hash=manifest.manifest_hash if manifest else None,
        supported_capability_count=(
            len(policy.supported_order_types) + len(policy.supported_actions)
            + len(policy.supported_time_in_force)
        ),
        blocked_capability_count=len(policy.blocked_capabilities),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=source_ok,
        capability_checks_passed=capability_ok,
        manifest_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        capability_manifest_created=passed,
        connection_authorized=False,
        paper_session_authorized=False,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False,
        account_accessed=False,
        session_opened=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        capability_policy=policy,
        manifest=manifest,
        reasons=[
            "Paper Broker Capability 범위가 선언되었습니다."
            if passed else "Paper Broker Capability Manifest가 차단되었습니다."
        ],
        warnings=all_errors + [
            "Capability 지원 표시는 실제 연결 또는 주문 권한이 아닙니다."
        ],
        next_actions=[
            "지원 및 차단 Capability 목록을 수동 검토합니다.",
            "실제 Broker API 또는 계좌정보를 사용하지 않습니다.",
        ],
    )


def save_capability_manifest_result(
    result: PaperBrokerCapabilityManifestResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_capability_manifest_{stamp}.json"
    latest = directory / "latest_paper_capability_manifest.json"
    payload = result.to_dict()
    for path in (report, latest):
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_capability_manifest_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.3":
        raise ValueError("V13.3 결과 파일이 아닙니다.")
    manifest = payload.get("manifest")
    if manifest:
        saved_hash = manifest.get("manifest_hash")
        hash_payload = dict(manifest)
        hash_payload.pop("manifest_hash", None)
        if saved_hash != calculate_manifest_hash(hash_payload):
            raise ValueError("저장된 Capability Manifest가 변조되었습니다.")
    return payload

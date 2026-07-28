import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_session_configuration import (
    PaperBrokerSessionConfiguration,
    PaperBrokerSessionConfigurationResult,
    verify_session_configuration,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_broker_connection_dry_run_validator"
)
REQUIRED_VALIDATION_TEXT = "VALIDATE PAPER CONNECTION WITHOUT CONNECTING"


@dataclass(frozen=True)
class PaperConnectionDryRunPolicy:
    required_source_version: str = "V13.1"
    required_source_status: str = "CONFIGURED"
    required_confirmation_text: str = REQUIRED_VALIDATION_TEXT
    required_environment: str = "PAPER"
    required_credential_mode: str = "NO_CREDENTIALS"
    required_connection_mode: str = "CONNECTION_DISABLED"
    minimum_ticket_count: int = 1
    require_same_operator: bool = True
    require_configuration_hash: bool = True
    dns_lookup_disabled: bool = True
    socket_creation_disabled: bool = True
    http_request_disabled: bool = True
    network_access_disabled: bool = True
    account_access_disabled: bool = True
    session_open_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DryRunCheck:
    check_name: str
    expected_value: str
    actual_value: str
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperConnectionDryRunCertificate:
    certificate_id: str
    created_at: str
    certificate_status: str
    configuration_id: str
    configuration_hash: str
    broker_profile: str
    environment: str
    operator: str
    ticket_count: int
    check_count: int
    checks: tuple[DryRunCheck, ...]
    connection_ready_for_future_review: bool
    connection_authorized: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    session_opened: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [item.to_dict() for item in self.checks]
        payload.pop("certificate_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [item.to_dict() for item in self.checks]
        return payload


@dataclass
class PaperConnectionDryRunResult:
    version: str
    created_at: str
    dry_run_result_id: str
    result_status: str
    result_status_label: str
    certificate_id: str | None
    certificate_hash: str | None
    check_count: int
    passed_check_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    dry_run_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    connection_dry_run_validated: bool
    connection_authorized: bool
    paper_session_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    session_opened: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    dry_run_policy: PaperConnectionDryRunPolicy
    certificate: PaperConnectionDryRunCertificate | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dry_run_policy"] = self.dry_run_policy.to_dict()
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None
        )
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def calculate_certificate_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperConnectionDryRunPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_source_version != "V13.1":
        errors.append("Source Version은 V13.1이어야 합니다.")
    if policy.required_environment != "PAPER":
        errors.append("PAPER 환경만 허용됩니다.")
    if policy.required_credential_mode != "NO_CREDENTIALS":
        errors.append("NO_CREDENTIALS만 허용됩니다.")
    if policy.required_connection_mode != "CONNECTION_DISABLED":
        errors.append("CONNECTION_DISABLED만 허용됩니다.")
    disabled = (
        policy.dns_lookup_disabled
        and policy.socket_creation_disabled
        and policy.http_request_disabled
        and policy.network_access_disabled
        and policy.account_access_disabled
        and policy.session_open_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    if not disabled:
        errors.append("모든 연결 및 실행 차단 정책이 필요합니다.")
    return errors


def validate_source(
    source: PaperBrokerSessionConfigurationResult,
    operator: str,
    policy: PaperConnectionDryRunPolicy,
) -> tuple[PaperBrokerSessionConfiguration | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperBrokerSessionConfigurationResult):
        return None, ["V13.1 Session Result 형식이 아닙니다."]
    if source.version != policy.required_source_version:
        errors.append("V13.1 Source가 아닙니다.")
    if source.result_status != policy.required_source_status:
        errors.append("CONFIGURED Source가 아닙니다.")
    configuration = source.configuration
    if configuration is None:
        errors.append("Session Configuration이 없습니다.")
        return None, errors
    valid, verify_errors = verify_session_configuration(configuration)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.paper_configuration_prepared:
        errors.append("안전하게 준비된 Session Source가 아닙니다.")
    if any(
        (
            source.session_opened,
            source.network_accessed,
            source.account_accessed,
            source.broker_api_called,
            source.order_submitted,
        )
    ):
        errors.append("연결 또는 실행 흔적이 있는 Source입니다.")
    if policy.require_same_operator and configuration.operator != operator:
        errors.append("Operator가 Source와 일치하지 않습니다.")
    return configuration, errors


def make_checks(
    configuration: PaperBrokerSessionConfiguration,
    policy: PaperConnectionDryRunPolicy,
) -> tuple[DryRunCheck, ...]:
    rows = (
        ("Environment", policy.required_environment, configuration.environment),
        ("Credential Mode", policy.required_credential_mode, configuration.credential_mode),
        ("Connection Mode", policy.required_connection_mode, configuration.connection_mode),
        ("Endpoint", "NONE", "NONE" if configuration.endpoint is None else "PRESENT"),
        (
            "Account Reference",
            "NONE",
            "NONE" if configuration.account_reference is None else "PRESENT",
        ),
        ("Ticket Count", f">={policy.minimum_ticket_count}", str(configuration.ticket_count)),
        ("Session Opened", "False", str(configuration.session_opened)),
        ("Network Accessed", "False", str(configuration.network_accessed)),
        ("Broker API Called", "False", str(configuration.broker_api_called)),
        ("Order Submitted", "False", str(configuration.order_submitted)),
    )
    checks: list[DryRunCheck] = []
    for name, expected, actual in rows:
        if name == "Ticket Count":
            passed = configuration.ticket_count >= policy.minimum_ticket_count
        elif expected == "False":
            passed = actual == "False"
        else:
            passed = expected == actual
        checks.append(DryRunCheck(name, expected, actual, passed))
    return tuple(checks)


def verify_dry_run_certificate(
    certificate: PaperConnectionDryRunCertificate,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if certificate.certificate_status != "VALIDATED":
        errors.append("Dry-Run Certificate가 VALIDATED 상태가 아닙니다.")
    if certificate.check_count != len(certificate.checks):
        errors.append("Check Count가 일치하지 않습니다.")
    if not certificate.checks or not all(item.passed for item in certificate.checks):
        errors.append("통과하지 못한 Dry-Run Check가 있습니다.")
    if certificate.connection_authorized:
        errors.append("Connection 권한이 열려 있습니다.")
    if any(
        (
            certificate.dns_lookup_performed,
            certificate.socket_created,
            certificate.http_request_sent,
            certificate.network_accessed,
            certificate.account_accessed,
            certificate.session_opened,
            certificate.broker_api_called,
            certificate.order_submitted,
            certificate.live_execution_authorized,
        )
    ):
        errors.append("실제 연결 또는 실행 흔적이 있습니다.")
    expected = calculate_certificate_hash(certificate.payload_without_hash())
    if expected != certificate.certificate_hash:
        errors.append("Dry-Run Certificate Hash가 일치하지 않습니다.")
    return not errors, errors


def validate_paper_broker_connection_dry_run(
    source: PaperBrokerSessionConfigurationResult,
    operator: str,
    confirmation_text: str,
    policy: PaperConnectionDryRunPolicy | None = None,
    now: datetime | None = None,
) -> PaperConnectionDryRunResult:
    policy = policy or PaperConnectionDryRunPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    configuration, source_errors = validate_source(source, clean_operator, policy)
    checks: tuple[DryRunCheck, ...] = ()
    if configuration is not None and not source_errors:
        checks = make_checks(configuration, policy)
    check_errors = (
        [] if checks and all(item.passed for item in checks)
        else ["Dry-Run Check가 모두 통과하지 못했습니다."]
    )
    certificate: PaperConnectionDryRunCertificate | None = None
    hash_ok = False
    all_errors = policy_errors + input_errors + source_errors + check_errors
    if not all_errors and configuration is not None:
        draft = PaperConnectionDryRunCertificate(
            certificate_id=str(uuid.uuid4()),
            created_at=created_at,
            certificate_status="VALIDATED",
            configuration_id=configuration.configuration_id,
            configuration_hash=configuration.configuration_hash,
            broker_profile=configuration.broker_profile,
            environment=configuration.environment,
            operator=clean_operator,
            ticket_count=configuration.ticket_count,
            check_count=len(checks),
            checks=checks,
            connection_ready_for_future_review=True,
            connection_authorized=False,
            dns_lookup_performed=False,
            socket_created=False,
            http_request_sent=False,
            network_accessed=False,
            account_accessed=False,
            session_opened=False,
            broker_api_called=False,
            order_submitted=False,
            live_execution_authorized=False,
            certificate_hash="",
        )
        certificate = PaperConnectionDryRunCertificate(
            **{
                **asdict(draft),
                "checks": draft.checks,
                "certificate_hash": calculate_certificate_hash(
                    draft.payload_without_hash()
                ),
            }
        )
        hash_ok, hash_errors = verify_dry_run_certificate(certificate)
        all_errors.extend(hash_errors)
    safety_ok = (
        policy.dns_lookup_disabled
        and policy.socket_creation_disabled
        and policy.http_request_disabled
        and policy.network_access_disabled
        and policy.account_access_disabled
        and policy.session_open_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    source_ok = not source_errors
    passed = (
        not policy_errors and not input_errors and source_ok
        and not check_errors and hash_ok and safety_ok and not all_errors
    )
    status = "VALIDATED" if passed else ("BLOCKED" if source_ok else "FAILED")
    return PaperConnectionDryRunResult(
        version="V13.2",
        created_at=created_at,
        dry_run_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "VALIDATED": "비연결 Dry-Run 검증 완료",
            "BLOCKED": "Dry-Run 입력 또는 검사 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        certificate_id=certificate.certificate_id if certificate else None,
        certificate_hash=certificate.certificate_hash if certificate else None,
        check_count=len(checks),
        passed_check_count=sum(item.passed for item in checks),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=source_ok,
        dry_run_checks_passed=bool(checks) and not check_errors,
        certificate_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        connection_dry_run_validated=passed,
        connection_authorized=False,
        paper_session_authorized=False,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        dns_lookup_performed=False,
        socket_created=False,
        http_request_sent=False,
        network_accessed=False,
        account_accessed=False,
        session_opened=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        dry_run_policy=policy,
        certificate=certificate,
        reasons=[
            "실제 연결 없이 Paper Connection 설정을 검증했습니다."
            if passed else "Paper Connection Dry-Run이 차단되었습니다."
        ],
        warnings=all_errors + [
            "V13.2는 DNS, Socket, HTTP 및 Broker 연결을 수행하지 않습니다."
        ],
        next_actions=[
            "Dry-Run Check와 Certificate Hash를 수동 검토합니다.",
            "실제 API Key 또는 계좌정보를 입력하지 않습니다.",
        ],
    )


def save_connection_dry_run_result(
    result: PaperConnectionDryRunResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_connection_dry_run_{stamp}.json"
    latest = directory / "latest_paper_connection_dry_run.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_connection_dry_run_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.2":
        raise ValueError("V13.2 결과 파일이 아닙니다.")
    certificate = payload.get("certificate")
    if certificate:
        saved_hash = certificate.get("certificate_hash")
        hash_payload = dict(certificate)
        hash_payload.pop("certificate_hash", None)
        if saved_hash != calculate_certificate_hash(hash_payload):
            raise ValueError("저장된 Dry-Run Certificate가 변조되었습니다.")
    return payload

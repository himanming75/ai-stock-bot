import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_adapter_foundation import (
    PaperBrokerAdapterPackage,
    PaperBrokerAdapterResult,
    verify_adapter_package,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_broker_session_configuration"
)
REQUIRED_CONFIGURATION_TEXT = "PREPARE PAPER BROKER SESSION CONFIGURATION"


@dataclass(frozen=True)
class PaperBrokerSessionPolicy:
    required_source_version: str = "V13.0"
    required_source_status: str = "PREPARED"
    required_confirmation_text: str = REQUIRED_CONFIGURATION_TEXT
    allowed_broker_profile: str = "GENERIC_PAPER"
    allowed_environment: str = "PAPER"
    required_credential_mode: str = "NO_CREDENTIALS"
    required_connection_mode: str = "CONNECTION_DISABLED"
    require_same_operator: bool = True
    require_source_hash: bool = True
    reject_secret_material: bool = True
    network_access_disabled: bool = True
    account_access_disabled: bool = True
    session_open_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerSessionConfiguration:
    configuration_id: str
    created_at: str
    configuration_status: str
    broker_profile: str
    environment: str
    credential_mode: str
    connection_mode: str
    endpoint: str | None
    account_reference: str | None
    adapter_package_id: str
    adapter_package_hash: str
    envelope_id: str
    trading_date: str
    operator: str
    ticket_count: int
    session_opened: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    configuration_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("configuration_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperBrokerSessionConfigurationResult:
    version: str
    created_at: str
    configuration_result_id: str
    result_status: str
    result_status_label: str
    configuration_id: str | None
    configuration_hash: str | None
    broker_profile: str
    environment: str
    ticket_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    secret_checks_passed: bool
    configuration_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    paper_configuration_prepared: bool
    paper_session_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    session_opened: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    session_policy: PaperBrokerSessionPolicy
    configuration: PaperBrokerSessionConfiguration | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["session_policy"] = self.session_policy.to_dict()
        payload["configuration"] = (
            self.configuration.to_dict()
            if self.configuration is not None else None
        )
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def calculate_configuration_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperBrokerSessionPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_source_version != "V13.0":
        errors.append("Source Version은 V13.0이어야 합니다.")
    if policy.allowed_environment != "PAPER":
        errors.append("Environment는 PAPER만 허용됩니다.")
    if policy.required_credential_mode != "NO_CREDENTIALS":
        errors.append("Credential Mode는 NO_CREDENTIALS여야 합니다.")
    if policy.required_connection_mode != "CONNECTION_DISABLED":
        errors.append("Connection Mode는 CONNECTION_DISABLED여야 합니다.")
    safety = (
        policy.network_access_disabled
        and policy.account_access_disabled
        and policy.session_open_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    if not safety:
        errors.append("모든 연결 및 실행 차단 정책이 필요합니다.")
    return errors


def validate_source(
    source: PaperBrokerAdapterResult,
    operator: str,
    policy: PaperBrokerSessionPolicy,
) -> tuple[PaperBrokerAdapterPackage | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperBrokerAdapterResult):
        return None, ["V13.0 Adapter Result 형식이 아닙니다."]
    if source.version != policy.required_source_version:
        errors.append("V13.0 Source가 아닙니다.")
    if source.result_status != policy.required_source_status:
        errors.append("PREPARED Source가 아닙니다.")
    package = source.adapter_package
    if package is None:
        errors.append("Adapter Package가 없습니다.")
        return None, errors
    valid, verify_errors = verify_adapter_package(package)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.paper_adapter_prepared:
        errors.append("검증된 Adapter Source가 아닙니다.")
    if source.network_accessed or source.account_accessed or source.broker_api_called:
        errors.append("연결 흔적이 있는 Source는 사용할 수 없습니다.")
    if policy.require_same_operator and package.operator != operator:
        errors.append("Operator가 Source와 일치하지 않습니다.")
    return package, errors


def contains_secret_material(values: dict[str, Any]) -> bool:
    secret_names = {
        "api_key", "api_secret", "access_token", "refresh_token",
        "password", "private_key", "account_number",
    }
    for key, value in values.items():
        normalized = str(key).strip().lower()
        if normalized in secret_names and value not in (None, "", False):
            return True
    return False


def verify_session_configuration(
    configuration: PaperBrokerSessionConfiguration,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if configuration.configuration_status != "CONFIGURED":
        errors.append("Configuration 상태가 CONFIGURED가 아닙니다.")
    if configuration.environment != "PAPER":
        errors.append("PAPER 환경이 아닙니다.")
    if configuration.credential_mode != "NO_CREDENTIALS":
        errors.append("Credential이 포함된 설정입니다.")
    if configuration.connection_mode != "CONNECTION_DISABLED":
        errors.append("Connection이 차단되지 않았습니다.")
    if configuration.endpoint is not None or configuration.account_reference is not None:
        errors.append("Endpoint 또는 Account 정보가 포함되었습니다.")
    if any(
        (
            configuration.session_opened,
            configuration.network_accessed,
            configuration.account_accessed,
            configuration.broker_api_called,
            configuration.order_submitted,
            configuration.live_execution_authorized,
        )
    ):
        errors.append("Session Configuration에 연결 또는 실행 흔적이 있습니다.")
    expected = calculate_configuration_hash(configuration.payload_without_hash())
    if expected != configuration.configuration_hash:
        errors.append("Configuration Hash가 일치하지 않습니다.")
    return not errors, errors


def build_paper_broker_session_configuration(
    source: PaperBrokerAdapterResult,
    operator: str,
    confirmation_text: str,
    requested_settings: dict[str, Any] | None = None,
    policy: PaperBrokerSessionPolicy | None = None,
    now: datetime | None = None,
) -> PaperBrokerSessionConfigurationResult:
    policy = policy or PaperBrokerSessionPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    settings = dict(requested_settings or {})
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    allowed_settings = {
        "broker_profile", "environment", "credential_mode", "connection_mode"
    }
    unknown = set(settings) - allowed_settings
    if unknown:
        input_errors.append("허용되지 않은 Session 설정 항목이 있습니다.")
    secret_errors: list[str] = []
    if policy.reject_secret_material and contains_secret_material(settings):
        secret_errors.append("API Key 또는 계좌 비밀정보 입력이 차단되었습니다.")
    broker_profile = settings.get("broker_profile", policy.allowed_broker_profile)
    environment = settings.get("environment", policy.allowed_environment)
    credential_mode = settings.get(
        "credential_mode", policy.required_credential_mode
    )
    connection_mode = settings.get(
        "connection_mode", policy.required_connection_mode
    )
    if broker_profile != policy.allowed_broker_profile:
        input_errors.append("Broker Profile이 허용되지 않습니다.")
    if environment != policy.allowed_environment:
        input_errors.append("PAPER 환경만 허용됩니다.")
    if credential_mode != policy.required_credential_mode:
        input_errors.append("Credential 사용은 허용되지 않습니다.")
    if connection_mode != policy.required_connection_mode:
        input_errors.append("Connection 활성화는 허용되지 않습니다.")
    package, source_errors = validate_source(source, clean_operator, policy)
    configuration: PaperBrokerSessionConfiguration | None = None
    hash_ok = False
    all_errors = policy_errors + input_errors + secret_errors + source_errors
    if not all_errors and package is not None:
        draft = PaperBrokerSessionConfiguration(
            configuration_id=str(uuid.uuid4()),
            created_at=created_at,
            configuration_status="CONFIGURED",
            broker_profile=broker_profile,
            environment=environment,
            credential_mode=credential_mode,
            connection_mode=connection_mode,
            endpoint=None,
            account_reference=None,
            adapter_package_id=package.adapter_package_id,
            adapter_package_hash=package.package_hash,
            envelope_id=package.envelope_id,
            trading_date=package.trading_date,
            operator=clean_operator,
            ticket_count=package.ticket_count,
            session_opened=False,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            order_submitted=False,
            live_execution_authorized=False,
            configuration_hash="",
        )
        configuration = PaperBrokerSessionConfiguration(
            **{
                **asdict(draft),
                "configuration_hash": calculate_configuration_hash(
                    draft.payload_without_hash()
                ),
            }
        )
        hash_ok, hash_errors = verify_session_configuration(configuration)
        all_errors.extend(hash_errors)
    safety_ok = (
        policy.network_access_disabled
        and policy.account_access_disabled
        and policy.session_open_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    passed = (
        not policy_errors and not input_errors and not secret_errors
        and not source_errors and hash_ok and safety_ok and not all_errors
    )
    source_ok = not source_errors
    status = "CONFIGURED" if passed else ("BLOCKED" if source_ok else "FAILED")
    return PaperBrokerSessionConfigurationResult(
        version="V13.1",
        created_at=created_at,
        configuration_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "CONFIGURED": "Paper Session 설정 준비 완료",
            "BLOCKED": "Session 입력 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        configuration_id=configuration.configuration_id if configuration else None,
        configuration_hash=(
            configuration.configuration_hash if configuration else None
        ),
        broker_profile=broker_profile,
        environment=environment,
        ticket_count=package.ticket_count if package else 0,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=source_ok,
        secret_checks_passed=not secret_errors,
        configuration_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        paper_configuration_prepared=passed,
        paper_session_authorized=False,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        session_opened=False,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        session_policy=policy,
        configuration=configuration,
        reasons=[
            "Paper Broker Session Configuration이 준비되었습니다."
            if passed else "Paper Broker Session Configuration이 차단되었습니다."
        ],
        warnings=all_errors + [
            "V13.1은 설정만 만들며 Broker Session을 열지 않습니다."
        ],
        next_actions=[
            "설정의 Broker Profile과 Hash를 수동 확인합니다.",
            "실제 API Key 또는 계좌번호를 입력하지 않습니다.",
        ],
    )


def save_session_configuration_result(
    result: PaperBrokerSessionConfigurationResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_broker_session_{stamp}.json"
    latest = directory / "latest_paper_broker_session.json"
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


def load_session_configuration_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.1":
        raise ValueError("V13.1 결과 파일이 아닙니다.")
    configuration = payload.get("configuration")
    if configuration:
        saved_hash = configuration.get("configuration_hash")
        hash_payload = dict(configuration)
        hash_payload.pop("configuration_hash", None)
        if saved_hash != calculate_configuration_hash(hash_payload):
            raise ValueError("저장된 Session Configuration이 변조되었습니다.")
    return payload

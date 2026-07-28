import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_broker_capability_manifest import (
    BLOCKED_CAPABILITIES,
    PaperBrokerCapabilityPolicy,
    build_paper_broker_capability_manifest,
    load_capability_manifest_result,
    save_capability_manifest_result,
    verify_capability_manifest,
)
from backtest.paper_broker_connection_dry_run_validator import (
    validate_paper_broker_connection_dry_run,
)
from test_paper_broker_connection_dry_run_validator import (
    create_source as create_v131_source,
)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    session = create_v131_source()
    return silent(
        validate_paper_broker_connection_dry_run,
        session,
        session.configuration.operator,
        "VALIDATE PAPER CONNECTION WITHOUT CONNECTING",
    )


def build(
    source: Any,
    operator: str | None = None,
    text: str = "BUILD PAPER BROKER CAPABILITY MANIFEST",
    policy: Any = None,
) -> Any:
    actual_operator = operator or (
        source.certificate.operator if source.certificate else "operator"
    )
    return silent(
        build_paper_broker_capability_manifest,
        source, actual_operator, text, policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(
        all(
            (
                not result.connection_authorized,
                not result.paper_session_authorized,
                not result.paper_execution_authorized,
                not result.automatic_execution_authorized,
                result.execution_blocked,
                not result.network_accessed,
                not result.account_accessed,
                not result.session_opened,
                not result.broker_api_called,
                not result.broker_order_created,
                not result.order_submitted,
                not result.live_order_created,
                not result.live_execution_authorized,
            )
        ),
        "연결 또는 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    declared = build(source)
    require(declared.result_status == "DECLARED", "Manifest가 생성되지 않았습니다.")
    require(declared.all_checks_passed, "정상 검사가 실패했습니다.")
    require(declared.manifest is not None, "Manifest가 없습니다.")
    require(declared.blocked_capability_count == 10, "10개 차단 기능이 없습니다.")
    valid, errors = verify_capability_manifest(declared.manifest)
    require(valid and not errors, "Manifest Hash 검사가 실패했습니다.")
    require_safe(declared)

    wrong_operator = build(source, operator="wrong-operator")
    require(wrong_operator.result_status == "FAILED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = build(source, text="ENABLE LIVE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    live_policy = PaperBrokerCapabilityPolicy(environment="LIVE")
    live = build(source, policy=live_policy)
    require(not live.all_checks_passed, "LIVE Policy가 차단되지 않았습니다.")
    options_policy = PaperBrokerCapabilityPolicy(
        supported_order_types=("MARKET", "LIMIT", "OPTION")
    )
    options = build(source, policy=options_policy)
    require(not options.all_checks_passed, "위험한 Order Type이 차단되지 않았습니다.")
    missing_block = PaperBrokerCapabilityPolicy(
        blocked_capabilities=BLOCKED_CAPABILITIES[:-1]
    )
    missing = build(source, policy=missing_block)
    require(not missing.all_checks_passed, "차단 기능 누락이 탐지되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.certificate, "broker_profile", "TAMPERED")
    tampered = build(tampered_source)
    require(tampered.result_status == "FAILED", "Source 변조가 실패 처리되지 않았습니다.")

    changed_manifest = replace(declared.manifest, environment="LIVE")
    valid_after_tamper, tamper_errors = verify_capability_manifest(changed_manifest)
    require(
        not valid_after_tamper and bool(tamper_errors),
        "Manifest 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_capability_manifest_result(
            declared, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_capability_manifest_result(latest)
        require(payload["version"] == "V13.3", "저장 Version이 다릅니다.")

    for result in (
        declared, wrong_operator, wrong_text, live, options, missing, tampered
    ):
        require_safe(result)

    checks = {
        "Version is V13.3": declared.version == "V13.3",
        "Default policy is valid": declared.policy_checks_passed,
        "Policy is immutable": PaperBrokerCapabilityPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not live.all_checks_passed,
        "Capability manifest was created": declared.capability_manifest_created,
        "MARKET and LIMIT are supported": declared.manifest.supported_order_types == ("MARKET", "LIMIT"),
        "BUY and SELL are supported": declared.manifest.supported_actions == ("BUY", "SELL"),
        "DAY time-in-force is supported": declared.manifest.supported_time_in_force == ("DAY",),
        "Ten dangerous capabilities blocked": declared.blocked_capability_count == 10,
        "Manifest hash passed": declared.manifest_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "LIVE environment was blocked": not live.all_checks_passed,
        "Unsupported order type was blocked": not options.all_checks_passed,
        "Missing blocked capability detected": not missing.all_checks_passed,
        "Source tampering failed": tampered.result_status == "FAILED",
        "Manifest tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.3",
        "Connection remains unauthorized": not declared.connection_authorized,
        "Broker API was not called": not declared.broker_api_called,
        "Order was not submitted": not declared.order_submitted,
        "Live execution not authorized": not declared.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.3 PAPER BROKER CAPABILITY MANIFEST TEST")
    print("=" * 92)
    print("V13.3 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.3 Validation Check가 실패했습니다.")
    print()
    print("V13.3 paper broker capability manifest test completed successfully.")
    print("지원 주문 범위, 10개 차단 기능, SHA-256 Manifest 및 변조 탐지가 검증되었습니다.")
    print("Network, 계좌, Broker API, 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()

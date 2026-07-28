import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_order_translation_validator import (
    PaperOrderTranslationPolicy,
    load_translation_result,
    save_translation_result,
    validate_paper_order_translation,
    verify_translation_batch,
)
from backtest.paper_broker_adapter_foundation import (
    build_paper_broker_adapter_package,
)
from backtest.paper_broker_session_configuration import (
    build_paper_broker_session_configuration,
)
from backtest.paper_broker_connection_dry_run_validator import (
    validate_paper_broker_connection_dry_run,
)
from backtest.paper_broker_capability_manifest import (
    build_paper_broker_capability_manifest,
)
from test_paper_broker_adapter_foundation import create_source as create_envelope


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_sources() -> tuple[Any, Any]:
    envelope = create_envelope()
    operator = envelope.envelope.operator
    adapter = silent(
        build_paper_broker_adapter_package, envelope, operator,
        "PREPARE PAPER BROKER ADAPTER",
    )
    session = silent(
        build_paper_broker_session_configuration, adapter, operator,
        "PREPARE PAPER BROKER SESSION CONFIGURATION",
    )
    dry_run = silent(
        validate_paper_broker_connection_dry_run, session, operator,
        "VALIDATE PAPER CONNECTION WITHOUT CONNECTING",
    )
    manifest = silent(
        build_paper_broker_capability_manifest, dry_run, operator,
        "BUILD PAPER BROKER CAPABILITY MANIFEST",
    )
    return manifest, adapter


def build(manifest: Any, adapter: Any, operator: str | None = None, text: str = "VALIDATE PAPER ORDER TRANSLATION", policy: Any = None) -> Any:
    actual = operator or manifest.manifest.operator
    return silent(
        validate_paper_order_translation,
        manifest, adapter, actual, text, policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(
        all((
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
        )),
        "실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    manifest, adapter = create_sources()
    result = build(manifest, adapter)
    require(result.result_status == "VALIDATED", "주문 변환이 검증되지 않았습니다.")
    require(result.translated_order_count == 2, "두 주문이 변환되지 않았습니다.")
    require(result.batch is not None, "Translation Batch가 없습니다.")
    require(all(not order.transmit for order in result.batch.orders), "transmit=False가 아닙니다.")
    valid, errors = verify_translation_batch(result.batch)
    require(valid and not errors, "Batch Hash 검사가 실패했습니다.")
    require_safe(result)

    wrong_operator = build(manifest, adapter, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "Operator 불일치가 차단되지 않았습니다.")
    wrong_text = build(manifest, adapter, text="SUBMIT")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = PaperOrderTranslationPolicy(order_submission_disabled=False)
    unsafe = build(manifest, adapter, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    bad_type_adapter = copy.deepcopy(adapter)
    bad_ticket = replace(
        bad_type_adapter.adapter_package.tickets[0], order_type="STOP"
    )
    object.__setattr__(
        bad_type_adapter.adapter_package,
        "tickets",
        (bad_ticket, *bad_type_adapter.adapter_package.tickets[1:]),
    )
    bad_type = build(manifest, bad_type_adapter)
    require(bad_type.result_status == "FAILED", "변조 Adapter가 실패 처리되지 않았습니다.")

    transmit_adapter = copy.deepcopy(adapter)
    transmit_ticket = replace(
        transmit_adapter.adapter_package.tickets[0], transmit=True
    )
    object.__setattr__(
        transmit_adapter.adapter_package,
        "tickets",
        (transmit_ticket, *transmit_adapter.adapter_package.tickets[1:]),
    )
    transmit = build(manifest, transmit_adapter)
    require(transmit.result_status == "FAILED", "transmit=True가 차단되지 않았습니다.")

    changed_batch = replace(result.batch, target_schema="TAMPERED")
    valid_after_tamper, tamper_errors = verify_translation_batch(changed_batch)
    require(not valid_after_tamper and tamper_errors, "Batch 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_translation_result(result, Path(directory))
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_translation_result(latest)
        require(payload["version"] == "V13.4", "저장 Version이 다릅니다.")

    for item in (result, wrong_operator, wrong_text, unsafe, bad_type, transmit):
        require_safe(item)

    checks = {
        "Version is V13.4": result.version == "V13.4",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": PaperOrderTranslationPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Two orders were translated": result.translated_order_count == 2,
        "All translated orders have transmit False": all(not x.transmit for x in result.batch.orders),
        "MARKET order mapping passed": any(x.order_kind == "MARKET" for x in result.batch.orders),
        "LIMIT order mapping passed": any(x.order_kind == "LIMIT" for x in result.batch.orders),
        "Source ticket hashes were created": all(bool(x.source_ticket_hash) for x in result.batch.orders),
        "Batch hash passed": result.batch_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Unsupported order type failed": bad_type.result_status == "FAILED",
        "Transmit True failed": transmit.result_status == "FAILED",
        "Batch tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.4",
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.4 PAPER ORDER TRANSLATION VALIDATOR TEST")
    print("=" * 92)
    print("V13.4 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.4 Validation Check가 실패했습니다.")
    print()
    print("V13.4 paper order translation validator test completed successfully.")
    print("MARKET/LIMIT 변환, Ticket Hash, Batch Hash 및 변조 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()

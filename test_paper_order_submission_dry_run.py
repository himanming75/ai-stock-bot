import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_order_submission_dry_run import (
    PaperOrderSubmissionDryRunPolicy,
    load_submission_dry_run_result,
    save_submission_dry_run_result,
    simulate_paper_order_submission,
    verify_submission_dry_run_batch,
)
from test_paper_order_translation_validator import create_sources
from backtest.paper_order_translation_validator import (
    validate_paper_order_translation,
)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    manifest, adapter = create_sources()
    return silent(
        validate_paper_order_translation,
        manifest, adapter, manifest.manifest.operator,
        "VALIDATE PAPER ORDER TRANSLATION",
    )


def build(source: Any, operator: str | None = None, text: str = "SIMULATE PAPER ORDER SUBMISSION", policy: Any = None) -> Any:
    actual = operator or (source.batch.operator if source.batch else "operator")
    return silent(
        simulate_paper_order_submission, source, actual, text, policy,
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
            not result.dns_lookup_performed,
            not result.socket_created,
            not result.http_request_sent,
            not result.network_accessed,
            not result.account_accessed,
            not result.broker_api_called,
            not result.broker_order_created,
            not result.order_submitted,
            not result.live_order_created,
            not result.live_execution_authorized,
        )),
        "제출 또는 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    simulated = build(source)
    require(simulated.result_status == "SIMULATED", "Submission Dry-Run이 실패했습니다.")
    require(simulated.receipt_count == 2, "두 Receipt가 생성되지 않았습니다.")
    require(simulated.batch is not None, "Dry-Run Batch가 없습니다.")
    require(
        all(
            receipt.simulation_outcome == "WOULD_SUBMIT"
            and not receipt.transmit and not receipt.submitted
            and receipt.broker_order_id is None
            for receipt in simulated.batch.receipts
        ),
        "Receipt 안전 상태가 올바르지 않습니다.",
    )
    valid, errors = verify_submission_dry_run_batch(simulated.batch)
    require(valid and not errors, "Dry-Run Batch 검사가 실패했습니다.")
    require_safe(simulated)

    wrong_operator = build(source, operator="wrong")
    require(wrong_operator.result_status == "FAILED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = build(source, text="SUBMIT REAL ORDER")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = PaperOrderSubmissionDryRunPolicy(order_submission_disabled=False)
    unsafe = build(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    transmit_source = copy.deepcopy(source)
    changed_order = replace(transmit_source.batch.orders[0], transmit=True)
    object.__setattr__(
        transmit_source.batch, "orders",
        (changed_order, *transmit_source.batch.orders[1:]),
    )
    transmit = build(transmit_source)
    require(transmit.result_status == "FAILED", "transmit=True Source가 실패 처리되지 않았습니다.")

    changed_receipt = replace(
        simulated.batch.receipts[0], submitted=True
    )
    changed_batch = replace(
        simulated.batch,
        receipts=(changed_receipt, *simulated.batch.receipts[1:]),
    )
    valid_after_tamper, tamper_errors = verify_submission_dry_run_batch(changed_batch)
    require(not valid_after_tamper and tamper_errors, "Receipt 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_submission_dry_run_result(
            simulated, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_submission_dry_run_result(latest)
        require(payload["version"] == "V13.5", "저장 Version이 다릅니다.")

    for result in (simulated, wrong_operator, wrong_text, unsafe, transmit):
        require_safe(result)

    checks = {
        "Version is V13.5": simulated.version == "V13.5",
        "Default policy is valid": simulated.policy_checks_passed,
        "Policy is immutable": PaperOrderSubmissionDryRunPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Submission dry-run completed": simulated.submission_dry_run_completed,
        "Two dry-run receipts were created": simulated.receipt_count == 2,
        "All outcomes are WOULD_SUBMIT": all(x.simulation_outcome == "WOULD_SUBMIT" for x in simulated.batch.receipts),
        "All receipts have transmit False": all(not x.transmit for x in simulated.batch.receipts),
        "No broker order IDs were created": all(x.broker_order_id is None for x in simulated.batch.receipts),
        "Receipt and batch hashes passed": simulated.batch_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Transmit True source failed": transmit.result_status == "FAILED",
        "Receipt tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.5",
        "DNS lookup was not performed": not simulated.dns_lookup_performed,
        "Socket was not created": not simulated.socket_created,
        "HTTP request was not sent": not simulated.http_request_sent,
        "Broker API was not called": not simulated.broker_api_called,
        "Broker order was not created": not simulated.broker_order_created,
        "Order was not submitted": not simulated.order_submitted,
        "Live execution not authorized": not simulated.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.5 PAPER ORDER SUBMISSION DRY-RUN TEST")
    print("=" * 92)
    print("V13.5 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.5 Validation Check가 실패했습니다.")
    print()
    print("V13.5 paper order submission dry-run test completed successfully.")
    print("WOULD_SUBMIT Receipt, SHA-256 Hash 및 제출 차단이 검증되었습니다.")
    print("DNS, Socket, HTTP, Broker API, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()

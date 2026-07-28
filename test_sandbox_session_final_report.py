import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import types
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# 다운로드 작업공간에 오래된 의존 파일이 없을 때만 V14.9의
# 최소 공개 형식을 테스트용으로 격리합니다. 전체 프로젝트에서는
# 실제 V14.9 모듈과 통합 테스트 Helper를 그대로 사용합니다.
COMPLETE_PROJECT = all(
    importlib.util.find_spec(name) is not None
    for name in (
        "backtest.paper_portfolio_valuation",
        "backtest.paper_broker_simulator",
    )
)

if not COMPLETE_PROJECT:
    ledger_stub = types.ModuleType(
        "backtest.sandbox_risk_decision_ledger"
    )

    @dataclass
    class SandboxRiskDecisionLedgerEntry:
        ledger_entry_id: str
        sequence: int
        recorded_at: str
        previous_entry_hash: str
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
            payload.pop("entry_hash")
            return payload

    @dataclass
    class SandboxRiskDecisionLedgerResult:
        version: str
        result_status: str
        all_checks_passed: bool
        ledger_entry_recorded: bool
        ledger_result_id: str
        total_entry_count: int
        latest_entry_id: str
        latest_entry_hash: str
        latest_decision_id: str
        latest_gate_action: str
        entries: tuple[SandboxRiskDecisionLedgerEntry, ...]
        paper_execution_authorized: bool = False
        automatic_execution_authorized: bool = False
        execution_blocked: bool = True
        credentials_used: bool = False
        market_data_api_called: bool = False
        network_accessed: bool = False
        account_accessed: bool = False
        broker_api_called: bool = False
        broker_order_created: bool = False
        order_submitted: bool = False
        live_order_created: bool = False
        live_execution_authorized: bool = False

    def stub_hash(payload: dict[str, Any]) -> str:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def verify_ledger_chain(
        entries: tuple[SandboxRiskDecisionLedgerEntry, ...],
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []
        previous_hash = "0" * 64
        for sequence, entry in enumerate(entries, start=1):
            if entry.sequence != sequence:
                errors.append("Ledger Sequence가 올바르지 않습니다.")
            if entry.previous_entry_hash != previous_hash:
                errors.append("Ledger Previous Hash가 올바르지 않습니다.")
            if entry.entry_hash != stub_hash(entry.payload_without_hash()):
                errors.append("Ledger Entry Hash가 올바르지 않습니다.")
            previous_hash = entry.entry_hash
        return not errors, errors

    ledger_stub.SandboxRiskDecisionLedgerEntry = (
        SandboxRiskDecisionLedgerEntry
    )
    ledger_stub.SandboxRiskDecisionLedgerResult = (
        SandboxRiskDecisionLedgerResult
    )
    ledger_stub.verify_ledger_chain = verify_ledger_chain
    sys.modules[
        "backtest.sandbox_risk_decision_ledger"
    ] = ledger_stub


from backtest.sandbox_session_final_report import (
    SandboxSessionFinalReportPolicy,
    generate_sandbox_session_final_report,
    load_final_report_result,
    save_final_report_result,
    verify_session_report,
)
if COMPLETE_PROJECT:
    from test_sandbox_risk_decision_gate import (
        apply_gate,
        create_source as create_risk_source,
    )
    from test_sandbox_risk_decision_ledger import record


NOW = datetime(2026, 7, 28, 14, 10, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    if COMPLETE_PROJECT:
        gate_result = apply_gate(create_risk_source())
        return record(gate_result)
    payload = {
        "ledger_entry_id": "ledger-entry-v15-0-001",
        "sequence": 1,
        "recorded_at": "2026-07-28T14:00:00+00:00",
        "previous_entry_hash": "0" * 64,
        "gate_decision_id": "gate-decision-v15-0-001",
        "gate_decision_hash": "a" * 64,
        "assessment_id": "assessment-v15-0-001",
        "session_id": "sandbox-session-v15-0-001",
        "operator": "operator-001",
        "source_risk_status": "SAFE",
        "source_risk_action": "ALLOW",
        "gate_action": "PROCEED",
        "manual_review_required": False,
        "sandbox_progress_allowed": True,
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
    entry = SandboxRiskDecisionLedgerEntry(
        **payload,
        entry_hash=stub_hash(payload),
    )
    return SandboxRiskDecisionLedgerResult(
        version="V14.9",
        result_status="RECORDED_IN_MEMORY",
        all_checks_passed=True,
        ledger_entry_recorded=True,
        ledger_result_id="ledger-result-v15-0-001",
        total_entry_count=1,
        latest_entry_id=entry.ledger_entry_id,
        latest_entry_hash=entry.entry_hash,
        latest_decision_id=entry.gate_decision_id,
        latest_gate_action=entry.gate_action,
        entries=(entry,),
    )


def finalize(
    source: Any,
    operator: str | None = None,
    text: str = "GENERATE IN MEMORY SANDBOX SESSION FINAL REPORT",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.entries[-1].operator
        if getattr(source, "entries", ()) else "operator-001"
    )
    return silent(
        generate_sandbox_session_final_report,
        source,
        operator or default_operator,
        text,
        policy,
        now,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(
        all(
            (
                not result.paper_execution_authorized,
                not result.automatic_execution_authorized,
                result.execution_blocked,
                not result.credentials_used,
                not result.market_data_api_called,
                not result.network_accessed,
                not result.account_accessed,
                not result.broker_api_called,
                not result.broker_order_created,
                not result.order_submitted,
                not result.live_order_created,
                not result.live_execution_authorized,
            )
        ),
        "V15.0 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    result = finalize(source)
    require(
        result.result_status == "FINALIZED_IN_MEMORY",
        "Sandbox Session Final Report 생성이 실패했습니다.",
    )
    require(result.final_report_generated, "Final Report가 없습니다.")
    require(result.report is not None, "Session Report가 없습니다.")
    require(result.total_decision_count == 1, "Decision Count가 다릅니다.")
    require(result.final_gate_action == "PROCEED", "Final Gate Action이 다릅니다.")
    require(
        result.final_session_outcome == "SANDBOX_COMPLETE",
        "Final Session Outcome이 다릅니다.",
    )
    require(
        result.report.source_latest_entry_hash == source.latest_entry_hash,
        "V14.9 Latest Entry Hash 연결이 다릅니다.",
    )
    report_valid, report_errors = verify_session_report(result.report)
    require(
        report_valid and not report_errors,
        "Session Report Hash 검사가 실패했습니다.",
    )
    require_safe(result)

    wrong_operator = finalize(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "잘못된 Operator가 차단되지 않았습니다.",
    )
    wrong_text = finalize(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "잘못된 확인 문구가 차단되지 않았습니다.",
    )
    unsafe_policy = SandboxSessionFinalReportPolicy(
        broker_api_disabled=False
    )
    unsafe = finalize(source, policy=unsafe_policy)
    require(
        not unsafe.all_checks_passed,
        "위험 Policy가 차단되지 않았습니다.",
    )
    wrong_type = finalize(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 형식이 실패 처리되지 않았습니다.",
    )
    backward = finalize(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 Final Report 시간이 차단되지 않았습니다.",
    )

    tampered_source = copy.deepcopy(source)
    changed_entry = replace(
        tampered_source.entries[0],
        gate_action="BLOCK",
    )
    tampered_source.entries = (changed_entry,)
    tampered = finalize(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Ledger가 실패 처리되지 않았습니다.",
    )

    broken_link = copy.deepcopy(source)
    broken_link.latest_entry_hash = "f" * 64
    broken = finalize(broken_link)
    require(
        broken.result_status == "BLOCKED",
        "잘못된 Latest Entry 연결이 차단되지 않았습니다.",
    )

    changed_report = replace(
        result.report,
        final_session_outcome="BLOCKED",
    )
    changed_valid, changed_errors = verify_session_report(changed_report)
    require(
        not changed_valid and changed_errors,
        "Final Report 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_final_report_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "V15.0 결과가 저장되지 않았습니다.",
        )
        payload = load_final_report_result(latest_path)
        require(payload["version"] == "V15.0", "저장 Version이 다릅니다.")
        require(
            payload["report"]["report_hash"] == result.report_hash,
            "저장 Report Hash가 다릅니다.",
        )

    for checked in (
        result,
        wrong_operator,
        wrong_text,
        unsafe,
        wrong_type,
        backward,
        tampered,
        broken,
    ):
        require_safe(checked)

    checks = {
        "Version is V15.0": result.version == "V15.0",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxSessionFinalReportPolicy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.9 ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.hash_chain_checks_passed,
        "Single session check passed": result.session_checks_passed,
        "Operator check passed": result.operator_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Source linkage check passed": result.linkage_checks_passed,
        "Final report was generated": result.final_report_generated,
        "Report SHA-256 hash passed": report_valid,
        "PROCEED mapped to SANDBOX_COMPLETE": (
            result.final_session_outcome == "SANDBOX_COMPLETE"
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Report tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V15.0",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())

    print("=" * 96)
    print("AI STOCK BOT V15.0 SANDBOX SESSION FINAL REPORT TEST")
    print("=" * 96)
    print("V15.0 VALIDATION CHECKS")
    print("-" * 96)
    for name, passed in checks.items():
        print(f"{name:<62}: {passed}")
    print("=" * 96)
    require(
        checks["All checks passed"],
        "V15.0 Validation Check가 실패했습니다.",
    )
    print()
    print("V15.0 sandbox session final report test completed successfully.")
    print(
        "V14.9 Ledger 연결, Session 요약, SHA-256 Report Hash 및 "
        "변조 차단이 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()

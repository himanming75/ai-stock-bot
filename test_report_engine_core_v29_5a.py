from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.report_engine_core_v29_5a as m
from backtest.report_engine_core_v29_5a import (
    MonteCarloInput,
    PerformanceInput,
    ProfessionalReport,
    ReportError,
    ReportPolicy,
    RiskInput,
    StressInput,
    WalkForwardInput,
    create_professional_report,
    load_report,
    save_report,
    verify_report,
)

def check(name, condition):
    print(f"{name:<108}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except ReportError:
        return True
    return False

performance = PerformanceInput(
    total_return_pct=Decimal("42.5"),
    cagr_pct=Decimal("18.2"),
    sharpe_ratio=Decimal("1.75"),
    sortino_ratio=Decimal("2.30"),
    calmar_ratio=Decimal("1.45"),
    profit_factor=Decimal("1.85"),
    win_rate=Decimal("0.58"),
    alpha_pct=Decimal("6.4"),
    information_ratio=Decimal("0.82"),
)

risk = RiskInput(
    max_drawdown_pct=Decimal("-12.5"),
    annualized_volatility_pct=Decimal("16.2"),
    value_at_risk_pct=Decimal("-2.4"),
    conditional_value_at_risk_pct=Decimal("-3.8"),
    exposure_ratio=Decimal("0.72"),
    ruin_probability=Decimal("0.01"),
)

walk_forward = WalkForwardInput(
    total_windows=8,
    profitable_window_ratio=Decimal("0.75"),
    average_out_of_sample_return_pct=Decimal("8.4"),
    parameter_stability_ratio=Decimal("0.75"),
    overfitting_risk_score=Decimal("24"),
    validation_passed=True,
)

monte_carlo = MonteCarloInput(
    simulation_count=1000,
    mean_terminal_return_pct=Decimal("36"),
    percentile_5_return_pct=Decimal("9"),
    loss_probability=Decimal("0.04"),
    ruin_probability=Decimal("0.00"),
    robustness_score=Decimal("88"),
    validation_passed=True,
)

stress = StressInput(
    scenario_count=7,
    survival_ratio=Decimal("0.86"),
    worst_terminal_return_pct=Decimal("-18"),
    worst_max_drawdown_pct=Decimal("-28"),
    average_resilience_score=Decimal("76"),
    stress_score=Decimal("79"),
    validation_passed=True,
)

source_hashes = (
    ("v29_0", "a" * 64),
    ("v29_1", "b" * 64),
    ("v29_2", "c" * 64),
    ("v29_3", "d" * 64),
    ("v29_4", "e" * 64),
)

timestamp = "2026-07-29T06:45:00+00:00"
report = create_professional_report(
    "AI Stock Bot Professional Strategy",
    performance,
    risk,
    walk_forward,
    monte_carlo,
    stress,
    source_hashes,
    report_timestamp=timestamp,
)

check("V29.5A version verified", m.VERSION == "29.5A")
check("Report ID created", report.report_id.startswith("RPT-"))
check("Strategy name retained", report.executive_summary.strategy_name == "AI Stock Bot Professional Strategy")
check("Report timestamp retained", report.executive_summary.report_timestamp == timestamp)
check("Five component scores created", len(report.component_scores) == 5)
check("Expected component set created",
      {x.name for x in report.component_scores} == {"PERFORMANCE","RISK","WALK_FORWARD","MONTE_CARLO","STRESS"})
check("Performance score calculated", next(x.score for x in report.component_scores if x.name=="PERFORMANCE") > Decimal("0"))
check("Risk score calculated", next(x.score for x in report.component_scores if x.name=="RISK") > Decimal("0"))
check("Walk-forward score calculated", next(x.score for x in report.component_scores if x.name=="WALK_FORWARD") > Decimal("0"))
check("Monte Carlo score calculated", next(x.score for x in report.component_scores if x.name=="MONTE_CARLO") > Decimal("0"))
check("Stress score calculated", next(x.score for x in report.component_scores if x.name=="STRESS") > Decimal("0"))
check("All component scores bounded", all(Decimal("0") <= x.score <= Decimal("100") for x in report.component_scores))
check("All component statuses generated", all(x.status in {"EXCELLENT","GOOD","ACCEPTABLE","WEAK","POOR"} for x in report.component_scores))
check("Overall score calculated", Decimal("0") <= report.executive_summary.overall_score <= Decimal("100"))
check("Overall grade generated", report.executive_summary.overall_grade in {"A","B","C","D","F"})
check("Recommendation generated",
      report.executive_summary.recommendation in {"RECOMMENDED_FOR_PAPER_TRADING","CONDITIONALLY_ACCEPTABLE","NOT_RECOMMENDED"})
check("Final validation passed", report.executive_summary.validation_passed)
check("Executive summary text generated", "Final recommendation" in report.executive_summary.summary_text)
check("Source hashes retained", len(report.source_hashes) == 5)
check("Report hash verified", verify_report(report))
check("Deterministic report returned",
      report == create_professional_report(
          "AI Stock Bot Professional Strategy",
          performance, risk, walk_forward, monte_carlo, stress,
          source_hashes, report_timestamp=timestamp
      ))

weak_report = create_professional_report(
    "Weak Strategy",
    replace(performance, cagr_pct=Decimal("-20"), sharpe_ratio=Decimal("-1"), sortino_ratio=Decimal("-1")),
    replace(risk, max_drawdown_pct=Decimal("-60"), annualized_volatility_pct=Decimal("50"), ruin_probability=Decimal("0.40")),
    replace(walk_forward, profitable_window_ratio=Decimal("0.20"), parameter_stability_ratio=Decimal("0.20"), overfitting_risk_score=Decimal("90"), validation_passed=False),
    replace(monte_carlo, loss_probability=Decimal("0.80"), ruin_probability=Decimal("0.50"), robustness_score=Decimal("10"), validation_passed=False),
    replace(stress, survival_ratio=Decimal("0.20"), average_resilience_score=Decimal("15"), stress_score=Decimal("10"), validation_passed=False),
    source_hashes,
    report_timestamp=timestamp,
)
check("Weak strategy is not recommended", weak_report.executive_summary.recommendation == "NOT_RECOMMENDED")
check("Weak strategy validation failed", not weak_report.executive_summary.validation_passed)

check("Missing strategy name blocked", blocked(lambda: create_professional_report(
    "", performance, risk, walk_forward, monte_carlo, stress, source_hashes, report_timestamp=timestamp
)))
check("Invalid win rate blocked", blocked(lambda: create_professional_report(
    "Bad", replace(performance, win_rate=Decimal("2")), risk, walk_forward, monte_carlo, stress, source_hashes, report_timestamp=timestamp
)))
check("Positive drawdown blocked", blocked(lambda: create_professional_report(
    "Bad", performance, replace(risk, max_drawdown_pct=Decimal("1")), walk_forward, monte_carlo, stress, source_hashes, report_timestamp=timestamp
)))
check("Invalid probability blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, replace(walk_forward, profitable_window_ratio=Decimal("2")), monte_carlo, stress, source_hashes, report_timestamp=timestamp
)))
check("Too few Monte Carlo simulations blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, walk_forward, replace(monte_carlo, simulation_count=50), stress, source_hashes, report_timestamp=timestamp
)))
check("Too few source hashes blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, walk_forward, monte_carlo, stress, source_hashes[:4], report_timestamp=timestamp
)))
check("Duplicate source hash names blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, walk_forward, monte_carlo, stress,
    source_hashes[:-1] + (("v29_0", "f"*64),), report_timestamp=timestamp
)))
check("Invalid source hash blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, walk_forward, monte_carlo, stress,
    source_hashes[:-1] + (("v29_4", "BAD"),), report_timestamp=timestamp
)))
check("Invalid timestamp blocked", blocked(lambda: create_professional_report(
    "Bad", performance, risk, walk_forward, monte_carlo, stress, source_hashes, report_timestamp="BAD"
)))
check("Invalid policy weights blocked", blocked(lambda: ReportPolicy(performance_weight=Decimal("0.5"))))
check("Invalid policy thresholds blocked", blocked(lambda: ReportPolicy(minimum_acceptable_score=Decimal("80"), minimum_recommended_score=Decimal("70"))))

tampered_report = replace(report, report_hash="BROKEN")
check("Tampered report detected", blocked(lambda: verify_report(tampered_report)))

tampered_grade = replace(
    report,
    executive_summary=replace(report.executive_summary, overall_grade="F"),
)
check("Tampered grade detected", blocked(lambda: verify_report(tampered_grade)))

tampered_component = replace(
    report,
    component_scores=(replace(report.component_scores[0], score=Decimal("999")),) + report.component_scores[1:],
)
check("Invalid component score detected", blocked(lambda: verify_report(tampered_component)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "professional_report.json"
    save_report(report, path)
    loaded = load_report(path)
    check("Professional report save and load passed", loaded == report)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["executive_summary"]["overall_score"] = "999"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved report blocked", blocked(lambda: load_report(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt", "yfinance"
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not(imports & forbidden))
check("Market data API was not called", not m.MARKET_DATA_API_CALLED)
check("Account API was not called", not m.ACCOUNT_API_CALLED)
check("Network was not accessed", not m.NETWORK_ACCESSED)
check("Broker API was not called", not m.BROKER_API_CALLED)
check("Broker order was not created", not m.BROKER_ORDER_CREATED)
check("Order was not submitted", not m.ORDER_SUBMITTED)
check("Live execution not authorized", not m.LIVE_EXECUTION_AUTHORIZED)
check("Funds were not reserved", not m.FUNDS_RESERVED)
check("Holdings were not reserved", not m.HOLDINGS_RESERVED)
check("All checks passed", True)

print("=" * 128)
print("V29.5A professional report engine core test completed successfully.")
print("Executive summary, weighted component scoring, overall grade, recommendation,")
print("V29.0-V29.4 source lineage, JSON persistence, SHA-256 integrity,")
print("and tamper detection passed.")
print("Market/account/network/broker/order/live execution remained blocked.")

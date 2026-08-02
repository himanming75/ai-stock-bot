const money = value =>
  new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"}).format(Number(value || 0));

const number = value =>
  new Intl.NumberFormat("en-US", {maximumFractionDigits:2}).format(Number(value || 0));

function renderDefinitionList(id, rows) {
  const target = document.getElementById(id);
  target.innerHTML = rows.map(([key, value]) =>
    `<dt>${key}</dt><dd>${value ?? "—"}</dd>`
  ).join("");
}

function setStatus(element, text, kind) {
  element.textContent = text || "UNKNOWN";
  element.className = element.className.split(" ")[0] + " " + kind;
}

async function refresh() {
  try {
    const response = await fetch("/api/dashboard", {cache:"no-store"});
    const data = await response.json();
    const runtime = data.runtime;
    const portfolio = data.portfolio;
    const signal = data.signal;
    const report = data.daily_report;

    document.getElementById("portfolio-value").textContent = money(portfolio.portfolio_value);
    document.getElementById("cash").textContent = money(portfolio.cash);
    document.getElementById("buying-power").textContent = money(portfolio.buying_power);
    document.getElementById("pnl").textContent = money(report.total_pnl);

    const overall = document.getElementById("overall-status");
    setStatus(overall, data.dashboard_state, data.dashboard_state === "READY" ? "good" : "bad");

    const runtimeStatus = document.getElementById("runtime-status");
    const runtimeKind = runtime.safe_mode ? "bad" :
      runtime.status === "PASS" ? "good" : "warn";
    setStatus(runtimeStatus, runtime.state, runtimeKind);

    renderDefinitionList("runtime-panel", [
      ["Status", runtime.status],
      ["Runtime ID", runtime.runtime_id || "Not assigned"],
      ["Pipeline ID", runtime.pipeline_id || "Not assigned"],
      ["Heartbeat", runtime.heartbeat_status],
      ["Heartbeat At", runtime.heartbeat_at || "Not available"],
      ["Single Tick", String(runtime.single_tick_only)],
      ["Continuous Loop", String(runtime.continuous_loop_enabled)],
    ]);

    const action = document.getElementById("signal-action");
    const actionValue = signal.approved_action || "HOLD";
    action.textContent = actionValue;
    action.className = `action ${actionValue.toLowerCase()}`;
    renderDefinitionList("signal-panel", [
      ["Symbol", signal.symbol || "No signal"],
      ["Requested", signal.requested_action || "—"],
      ["Approved", actionValue],
      ["Confidence", number(signal.confidence)],
      ["Quantity", number(signal.quantity)],
      ["Reference Price", money(signal.reference_price)],
      ["Pipeline State", signal.pipeline_state],
      ["Reason", (signal.reasons || []).join(", ") || "None"],
    ]);

    const accountStatus = document.getElementById("account-status");
    setStatus(accountStatus, portfolio.status,
      portfolio.status === "ACTIVE" ? "good" : "warn");
    renderDefinitionList("portfolio-panel", [
      ["Equity", money(portfolio.equity)],
      ["Cash", money(portfolio.cash)],
      ["Buying Power", money(portfolio.buying_power)],
      ["Portfolio Value", money(portfolio.portfolio_value)],
      ["Open Orders", number(portfolio.open_order_count)],
      ["Positions", number(portfolio.position_count)],
    ]);

    document.getElementById("buy-count").textContent = report.buy_count;
    document.getElementById("sell-count").textContent = report.sell_count;
    document.getElementById("hold-count").textContent = report.hold_count;
    document.getElementById("risk-count").textContent = report.risk_block_count;

    const reportStatus = document.getElementById("report-status");
    setStatus(reportStatus, report.report_ready ? "READY" : "WAITING",
      report.report_ready ? "good" : "warn");
    renderDefinitionList("report-panel", [
      ["Signals", report.signal_count],
      ["Errors", report.error_count],
      ["PnL", money(report.total_pnl)],
      ["Max Drawdown", `${number(report.max_drawdown_pct)}%`],
      ["Runtime", `${report.runtime_seconds}s`],
    ]);

    document.getElementById("last-refresh").textContent =
      `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    const overall = document.getElementById("overall-status");
    setStatus(overall, "DATA ERROR", "bad");
  }
}

refresh();
setInterval(refresh, 5000);

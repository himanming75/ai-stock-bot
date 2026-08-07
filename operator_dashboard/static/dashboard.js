function pretty(value) {
  return JSON.stringify(value || {}, null, 2);
}

function renderCandidates(rows) {
  const body = document.querySelector("#candidateTable tbody");
  body.innerHTML = (rows || []).map((row) => {
    const action = String(row.action || "HOLD").toLowerCase();
    return `<tr>
      <td>${row.symbol || ""}</td>
      <td class="${action}">${row.action || "HOLD"}</td>
      <td>${Number(row.confidence || 0).toFixed(3)}</td>
      <td>${row.market_regime || ""}</td>
      <td>${Number(row.reward_risk || 0).toFixed(2)}</td>
    </tr>`;
  }).join("");
}

function renderOrders(rows) {
  const body = document.querySelector("#orderTable tbody");
  body.innerHTML = (rows || []).map((row) => `<tr>
    <td>${row.cycle_id || ""}</td>
    <td>${row.symbol || ""}</td>
    <td>${row.side || ""}</td>
    <td>${row.status || ""}</td>
    <td>${String(row.paper)}</td>
  </tr>`).join("");
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  const operator = data.operator || {};
  const safety = data.safety || {};
  const consoleData = data.operation_console || {};
  const stage = consoleData.session_stage || {};

  document.getElementById("runtimeStatus").textContent =
    operator.runtime_status || "UNKNOWN";
  document.getElementById("paperBroker").textContent =
    safety.paper_broker || "ALPACA";
  document.getElementById("liveBroker").textContent =
    safety.live_broker || "ETRADE";
  document.getElementById("liveWrite").textContent =
    safety.live_write_enabled ? "ON" : "OFF";
  document.getElementById("emergencyState").textContent =
    String(operator.emergency_stop || false).toUpperCase();

  document.getElementById("sessionStage").textContent =
    stage.stage || "UNKNOWN";
  document.getElementById("sessionMessage").textContent =
    stage.message || "";

  renderCandidates(consoleData.ai_candidates);
  renderOrders(consoleData.orders);

  document.getElementById("watchlist").innerHTML =
    (consoleData.watchlist || [])
      .map((symbol) => `<span class="chip">${symbol}</span>`)
      .join("");

  document.getElementById("fillsPanel").textContent =
    pretty(consoleData.fills);
  document.getElementById("accountPanel").textContent =
    pretty(consoleData.account_summary);
  document.getElementById("positionsPanel").textContent =
    pretty(data.positions);
  document.getElementById("riskPanel").textContent = pretty(data.risk);
  document.getElementById("paperPanel").textContent = pretty(data.paper);
  document.getElementById("logPanel").textContent = pretty(data.logs);

  const phases = data.phases || {};
  document.getElementById("phasePanel").innerHTML =
    Object.entries(phases).map(([name, value]) => {
      const status = value.status || "NOT FOUND";
      return `<div class="phase-box">
        <strong>${name.toUpperCase()}</strong>
        <div class="${status === "PASS" ? "pass" : "off"}">
          ${status}
        </div>
      </div>`;
    }).join("");
}

async function runAction(action) {
  const response = await fetch("/api/action", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({action}),
  });
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "Action failed");
  }
  await loadStatus();
}

document.querySelectorAll("button[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    runAction(button.dataset.action);
  });
});

loadStatus();
setInterval(loadStatus, 5000);

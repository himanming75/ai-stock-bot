let statusData = {};

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function render() {
  const overall = document.getElementById(
    "overall"
  );
  overall.textContent =
    statusData.overall_status || "UNKNOWN";
  overall.className =
    "pill "
    + (
      statusData.overall_status === "READY"
        ? "ready"
        : "degraded"
    );

  document.getElementById(
    "updated"
  ).textContent =
    statusData.generated_at || "No timestamp";

  const values = [
    [
      "Controller",
      statusData.controller?.state || "UNKNOWN",
    ],
    [
      "Watchdog",
      statusData.watchdog?.state || "UNKNOWN",
    ],
    [
      "Daily Session",
      statusData.daily_session?.state
        || "UNKNOWN",
    ],
    [
      "Polling Lines",
      statusData.polling?.line_count || 0,
    ],
  ];
  document.getElementById(
    "cards"
  ).innerHTML = values.map(
    ([label, value]) => `
      <article class="card">
        <span>${label}</span>
        <strong>${value}</strong>
      </article>
    `
  ).join("");

  document.getElementById(
    "controller"
  ).textContent = pretty(
    statusData.controller?.summary || {}
  );
  document.getElementById(
    "watchdog"
  ).textContent = pretty(
    statusData.watchdog?.summary || {}
  );
  document.getElementById(
    "session"
  ).textContent = pretty(
    statusData.daily_session?.summary || {}
  );
  document.getElementById(
    "polling"
  ).textContent = pretty(
    statusData.polling || {}
  );
}

async function refresh() {
  const response = await fetch(
    "/api/status",
    {cache: "no-store"},
  );
  statusData = await response.json();
  render();
}

async function plan(action) {
  const response = await fetch(
    "/api/command-plan",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action,
        requested_by: "LOCAL_USER",
        reason: document.getElementById(
          "reason"
        ).value,
      }),
    },
  );
  const data = await response.json();
  document.getElementById(
    "plan"
  ).textContent = pretty(data);
}

document.querySelectorAll(
  "[data-action]"
).forEach(button => {
  button.addEventListener("click", () => {
    plan(button.dataset.action);
  });
});

refresh();
setInterval(refresh, 5000);

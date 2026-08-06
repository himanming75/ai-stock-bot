let currentView = "overview";
let dashboard = {};
let accounts = [];
let positions = [];
let orders = [];
let reconciliation = {};

const titleMap = {
  overview: "Multi-Broker Overview",
  accounts: "Accounts",
  positions: "Positions",
  orders: "Orders",
  reconciliation: "Reconciliation",
};

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function getJson(path) {
  const response = await fetch(path, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(
      `${path}: HTTP ${response.status}`
    );
  }
  return response.json();
}

function metrics() {
  const totals = dashboard.totals || {};
  const values = [
    ["Brokers", totals.brokers || 0],
    ["Accounts", totals.accounts || 0],
    ["Positions", totals.positions || 0],
    ["Orders", totals.orders || 0],
    [
      "Issues",
      totals.reconciliation_issues || 0,
    ],
    ["Errors", totals.errors || 0],
  ];
  document.getElementById("summary").innerHTML =
    values.map(([name, value]) => `
      <div class="metric">
        <span>${esc(name)}</span>
        <strong>${esc(value)}</strong>
      </div>
    `).join("");
}

function brokerCards() {
  const cards = dashboard.broker_cards || [];
  const element = document.getElementById(
    "broker-cards"
  );
  if (!cards.length) {
    element.innerHTML = `
      <div class="broker-card">
        No broker snapshot is available.
      </div>
    `;
    return;
  }
  element.innerHTML = cards.map(card => `
    <article class="broker-card ${
      card.status === "CONNECTED"
        ? "connected"
        : ""
    }">
      <h3>${esc(card.broker)}</h3>
      <dl>
        <dt>Status</dt>
        <dd>${esc(card.status)}</dd>
        <dt>Freshness</dt>
        <dd>${esc(card.freshness)}</dd>
        <dt>Accounts</dt>
        <dd>${esc(card.account_count)}</dd>
        <dt>Positions</dt>
        <dd>${esc(card.position_count)}</dd>
        <dt>Orders</dt>
        <dd>${esc(card.order_count)}</dd>
      </dl>
    </article>
  `).join("");
}

function table(items, preferredColumns) {
  if (!items.length) {
    return `<div class="empty">No records.</div>`;
  }
  const available = new Set();
  items.forEach(item => {
    Object.keys(item).forEach(key => {
      if (key !== "raw") available.add(key);
    });
  });
  const columns = [
    ...preferredColumns.filter(
      key => available.has(key)
    ),
    ...[...available].filter(
      key => !preferredColumns.includes(key)
    ).slice(0, 6),
  ];
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            ${columns.map(
              key => `<th>${esc(key)}</th>`
            ).join("")}
          </tr>
        </thead>
        <tbody>
          ${items.map(item => `
            <tr>
              ${columns.map(key => `
                <td>${esc(
                  typeof item[key] === "object"
                    ? JSON.stringify(item[key])
                    : item[key]
                )}</td>
              `).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function overviewContent() {
  const sources = (
    reconciliation.sources || []
  );
  return table(
    sources,
    [
      "broker",
      "available",
      "freshness",
      "generated_at",
      "age_seconds",
      "error",
    ],
  );
}

function reconciliationContent() {
  const issues = reconciliation.issues || [];
  const errors = reconciliation.errors || [];
  if (!issues.length && !errors.length) {
    return `
      <div class="empty">
        No reconciliation issues or errors.
      </div>
    `;
  }
  return [
    ...errors.map(item => `
      <div class="issue error">
        <strong>${esc(
          item.broker || "ERROR"
        )}</strong>
        <div>${esc(
          item.error || JSON.stringify(item)
        )}</div>
      </div>
    `),
    ...issues.map(item => `
      <div class="issue">
        <strong>${esc(
          item.issue_type || "ISSUE"
        )}</strong>
        <div>${esc(item.message || "")}</div>
        <small>
          ${esc(item.broker_left)}:
          ${esc(item.left_value)}
          → ${esc(item.broker_right)}:
          ${esc(item.right_value)}
        </small>
      </div>
    `),
  ].join("");
}

function renderContent() {
  document.getElementById(
    "page-title"
  ).textContent = titleMap[currentView];
  document.getElementById(
    "table-title"
  ).textContent = titleMap[currentView];

  let html = "";
  if (currentView === "overview") {
    html = overviewContent();
  } else if (currentView === "accounts") {
    html = table(
      accounts,
      [
        "broker",
        "account_id_masked",
        "account_type",
        "status",
        "cash",
        "buying_power",
        "equity",
        "market_value",
      ],
    );
  } else if (currentView === "positions") {
    html = table(
      positions,
      [
        "broker",
        "symbol",
        "security_type",
        "side",
        "quantity",
        "average_price",
        "market_price",
        "market_value",
        "unrealized_pl",
      ],
    );
  } else if (currentView === "orders") {
    html = table(
      orders,
      [
        "broker",
        "order_id",
        "symbol",
        "side",
        "order_type",
        "status",
        "quantity",
        "filled_quantity",
        "limit_price",
      ],
    );
  } else {
    html = reconciliationContent();
  }
  document.getElementById(
    "content"
  ).innerHTML = html;
}

async function refresh() {
  try {
    [
      dashboard,
      accounts,
      positions,
      orders,
      reconciliation,
    ] = await Promise.all([
      getJson("/api/dashboard"),
      getJson("/api/accounts"),
      getJson("/api/positions"),
      getJson("/api/orders"),
      getJson("/api/reconciliation"),
    ]);

    const overall = document.getElementById(
      "overall"
    );
    overall.textContent =
      dashboard.overall_status || "UNKNOWN";
    overall.className =
      "status "
      + (
        dashboard.overall_status === "HEALTHY"
          ? "healthy"
          : "degraded"
      );

    document.getElementById(
      "updated"
    ).textContent = dashboard.generated_at
      ? `Updated ${dashboard.generated_at}`
      : "No generated timestamp";

    metrics();
    brokerCards();
    renderContent();
  } catch (error) {
    document.getElementById(
      "overall"
    ).textContent = "ERROR";
    document.getElementById(
      "overall"
    ).className = "status degraded";
    document.getElementById(
      "content"
    ).innerHTML = `
      <div class="issue error">
        ${esc(error.message)}
      </div>
    `;
  }
}

document.querySelectorAll(
  "nav button"
).forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(
      "nav button"
    ).forEach(item => {
      item.classList.remove("active");
    });
    button.classList.add("active");
    currentView = button.dataset.view;
    renderContent();
  });
});

document.getElementById(
  "refresh"
).addEventListener("click", refresh);

refresh();
setInterval(refresh, 5000);

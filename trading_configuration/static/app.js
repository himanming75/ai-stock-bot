let schema = {};
let current = {};

function strategyCard(name, item) {
  return `
    <article class="strategy">
      <label>
        <span>
          <input type="checkbox"
                 data-strategy="${name}"
                 data-field="enabled"
                 ${item.enabled ? "checked" : ""}>
          ${name}
        </span>
      </label>
      <label>
        Weight
        <input type="number"
               min="0" max="10" step="0.1"
               data-strategy="${name}"
               data-field="weight"
               value="${item.weight ?? 1}">
      </label>
    </article>
  `;
}

function setProfile(key) {
  const profile = schema.profiles[key];
  if (!profile) return;
  document.getElementById(
    "trading-style"
  ).value = profile.trading_style;
  document.getElementById(
    "max-positions"
  ).value = profile.max_positions;
  document.getElementById(
    "max-position-percent"
  ).value = profile.max_position_percent;
  document.getElementById(
    "max-daily-loss"
  ).value = profile.max_daily_loss_percent;
  document.getElementById(
    "cash-reserve"
  ).value = profile.cash_reserve_percent;
  document.getElementById(
    "allow-short"
  ).checked = profile.allow_short;
  document.getElementById(
    "extended-hours"
  ).checked =
    profile.allow_extended_hours;
}

function collect() {
  const strategies = {};
  document.querySelectorAll(
    "[data-strategy]"
  ).forEach(element => {
    const name = element.dataset.strategy;
    strategies[name] ||= {};
    strategies[name][element.dataset.field] =
      element.type === "checkbox"
        ? element.checked
        : Number(element.value);
  });

  return {
    profile_key: document.getElementById(
      "profile-key"
    ).value,
    profile: {
      trading_style: document.getElementById(
        "trading-style"
      ).value,
      max_positions: Number(
        document.getElementById(
          "max-positions"
        ).value
      ),
      max_position_percent: Number(
        document.getElementById(
          "max-position-percent"
        ).value
      ),
      max_daily_loss_percent: Number(
        document.getElementById(
          "max-daily-loss"
        ).value
      ),
      cash_reserve_percent: Number(
        document.getElementById(
          "cash-reserve"
        ).value
      ),
      allow_short: document.getElementById(
        "allow-short"
      ).checked,
      allow_extended_hours:
        document.getElementById(
          "extended-hours"
        ).checked,
    },
    capital_limit: Number(
      document.getElementById(
        "capital-limit"
      ).value
    ),
    symbols: document.getElementById(
      "symbols"
    ).value,
    account_scope: "ALL_READ_ONLY",
    strategies,
  };
}

async function post(path) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(collect()),
  });
  const data = await response.json();
  document.getElementById(
    "result"
  ).textContent = JSON.stringify(
    data,
    null,
    2,
  );
}

async function initialize() {
  [schema, current] = await Promise.all([
    fetch("/api/schema").then(
      response => response.json()
    ),
    fetch("/api/current").then(
      response => response.json()
    ),
  ]);

  const profileSelect = document.getElementById(
    "profile-key"
  );
  profileSelect.innerHTML = Object.entries(
    schema.profiles
  ).map(([key, item]) => `
    <option value="${key}">
      ${item.display_name}
    </option>
  `).join("");

  const selected = (
    current.profile_key || "READ_ONLY"
  );
  profileSelect.value = selected;

  const profile = (
    current.profile
    || schema.profiles[selected]
  );
  document.getElementById(
    "trading-style"
  ).value = profile.trading_style;
  document.getElementById(
    "max-positions"
  ).value = profile.max_positions;
  document.getElementById(
    "max-position-percent"
  ).value = profile.max_position_percent;
  document.getElementById(
    "max-daily-loss"
  ).value = profile.max_daily_loss_percent;
  document.getElementById(
    "cash-reserve"
  ).value = profile.cash_reserve_percent;
  document.getElementById(
    "allow-short"
  ).checked = profile.allow_short;
  document.getElementById(
    "extended-hours"
  ).checked =
    profile.allow_extended_hours;
  document.getElementById(
    "capital-limit"
  ).value = current.capital_limit || 0;
  document.getElementById(
    "symbols"
  ).value = (
    current.symbols || []
  ).join(", ");

  const strategies = (
    current.strategies
    || schema.strategy_defaults
  );
  document.getElementById(
    "strategies"
  ).innerHTML = Object.entries(
    strategies
  ).map(
    ([name, item]) => strategyCard(
      name,
      item,
    )
  ).join("");

  profileSelect.addEventListener(
    "change",
    () => setProfile(profileSelect.value),
  );
}

document.getElementById(
  "validate"
).addEventListener(
  "click",
  () => post("/api/validate"),
);
document.getElementById(
  "save"
).addEventListener(
  "click",
  () => post("/api/save-draft"),
);

initialize();

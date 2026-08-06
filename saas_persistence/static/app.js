let token = localStorage.getItem("saas_token") || "";
let currentWorkspace = "";

const $ = (id) => document.getElementById(id);
const message = (text) => {
  $("appMessage").textContent = text;
};

async function api(path, body, auth = true) {
  const headers = {"Content-Type": "application/json"};
  if (auth && token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(path, {
    method: "POST",
    headers,
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function showDashboard() {
  $("authPanel").classList.add("hidden");
  $("dashboard").classList.remove("hidden");
}

async function loadWorkspaces() {
  const items = await api("/api/workspaces", {});
  const select = $("workspaceSelect");
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.workspace_id;
    option.textContent = `${item.name} (${item.role})`;
    select.appendChild(option);
  });
  currentWorkspace = select.value;
  await loadSummary();
}

async function loadSummary() {
  currentWorkspace = $("workspaceSelect").value;
  const summary = await api(
    "/api/workspace/summary",
    {workspace_id: currentWorkspace}
  );
  $("summaryOutput").textContent = JSON.stringify(summary, null, 2);
  $("strategy").value = summary.settings.selected_strategy;
  $("riskProfile").value = summary.settings.risk_profile;
  $("maxPositionWeight").value = summary.settings.max_position_weight;
  $("dailyLossLimit").value = summary.settings.daily_loss_limit;
}

$("loginTab").onclick = () => {
  $("loginTab").classList.add("active");
  $("registerTab").classList.remove("active");
  $("loginForm").classList.remove("hidden");
  $("registerForm").classList.add("hidden");
};

$("registerTab").onclick = () => {
  $("registerTab").classList.add("active");
  $("loginTab").classList.remove("active");
  $("registerForm").classList.remove("hidden");
  $("loginForm").classList.add("hidden");
};

$("registerForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("/api/register", {
      email: $("registerEmail").value,
      password: $("registerPassword").value,
      workspace_name: $("workspaceName").value,
    }, false);
    $("authMessage").textContent = "Registered. Please log in.";
    $("loginTab").click();
  } catch (error) {
    $("authMessage").textContent = error.message;
  }
};

$("loginForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    const result = await api("/api/login", {
      email: $("loginEmail").value,
      password: $("loginPassword").value,
    }, false);
    token = result.access_token;
    localStorage.setItem("saas_token", token);
    showDashboard();
    await loadWorkspaces();
  } catch (error) {
    $("authMessage").textContent = error.message;
  }
};

$("refreshButton").onclick = loadSummary;
$("workspaceSelect").onchange = loadSummary;

$("strategyForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("/api/workspace/strategy", {
      workspace_id: currentWorkspace,
      strategy: $("strategy").value,
    });
    message("Strategy saved.");
    await loadSummary();
  } catch (error) {
    message(error.message);
  }
};

$("riskForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("/api/workspace/risk", {
      workspace_id: currentWorkspace,
      risk_profile: $("riskProfile").value,
      max_position_weight: Number($("maxPositionWeight").value),
      daily_loss_limit: Number($("dailyLossLimit").value),
    });
    message("Risk settings saved.");
    await loadSummary();
  } catch (error) {
    message(error.message);
  }
};

$("brokerForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("/api/workspace/broker", {
      workspace_id: currentWorkspace,
      broker: $("broker").value,
      environment: $("environment").value,
      account_alias: $("accountAlias").value,
    });
    message("Broker metadata added. Credentials were not stored.");
    await loadSummary();
  } catch (error) {
    message(error.message);
  }
};

$("memberForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("/api/workspace/member", {
      workspace_id: currentWorkspace,
      member_email: $("memberEmail").value,
      role: $("memberRole").value,
    });
    message("Member added.");
    await loadSummary();
  } catch (error) {
    message(error.message);
  }
};

$("auditButton").onclick = async () => {
  try {
    const audit = await api("/api/workspace/audit", {
      workspace_id: currentWorkspace,
    });
    $("auditOutput").textContent = JSON.stringify(audit, null, 2);
  } catch (error) {
    message(error.message);
  }
};

if (token) {
  showDashboard();
  loadWorkspaces().catch(() => {
    localStorage.removeItem("saas_token");
    token = "";
    $("dashboard").classList.add("hidden");
    $("authPanel").classList.remove("hidden");
  });
}

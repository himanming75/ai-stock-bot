let data = {};

function pretty(value) {
  return JSON.stringify(value || {}, null, 2);
}

function render() {
  const certification = data.certification || {};
  const health = data.health || {};
  const session = data.session || {};
  const runtime = data.runtime || {};
  const backup = data.backup || {};
  const notification = data.notification || {};

  const overall = document.getElementById(
    "overall"
  );
  const status = certification.status || "NO DATA";
  overall.textContent =
    status === "PASS"
      ? "PASS / 통과"
      : `${status} / 상태 확인 필요`;
  overall.className =
    "pill " + (
      status === "PASS" ? "ready" : ""
    );

  document.getElementById(
    "updated"
  ).textContent =
    certification.stage
      ? `${certification.stage}`
      : "No report / 보고서 없음";

  const cards = [
    [
      "Health Score / 시스템 상태 점수",
      health.score ?? 0,
    ],
    [
      "Configuration / 설정",
      certification.approval_candidate_ready
        ? "READY / 준비 완료"
        : "NOT READY / 미완료",
    ],
    [
      "Session / 거래 세션",
      session.planned_action || "UNKNOWN",
    ],
    [
      "Commands / 명령 계획",
      certification.command_plan_count || 0,
    ],
    [
      "Backup / 백업",
      backup.mode || "NO PLAN",
    ],
    [
      "Notification / 알림",
      notification.delivery_status || "NO PREVIEW",
    ],
  ];

  document.getElementById(
    "cards"
  ).innerHTML = cards.map(
    ([label, value]) => `
      <article class="card">
        <span>${label}</span>
        <strong>${value}</strong>
      </article>
    `
  ).join("");

  document.getElementById(
    "session"
  ).textContent = pretty(session);
  document.getElementById(
    "runtime"
  ).textContent = pretty(runtime);
  document.getElementById(
    "backup"
  ).textContent = pretty(backup);
  document.getElementById(
    "notification"
  ).textContent = pretty(notification);
  document.getElementById(
    "report"
  ).textContent = pretty(data.report);
}

async function refresh() {
  const response = await fetch(
    "/api/dashboard",
    {cache: "no-store"},
  );
  data = await response.json();
  render();
}

refresh();
setInterval(refresh, 5000);

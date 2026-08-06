let data = {};
function pretty(v){return JSON.stringify(v||{},null,2)}
function render(){
  const report=data.report||{};
  const cert=data.certification||{};
  document.getElementById("overall").textContent =
    cert.status==="PASS" ? "PASS / 통과" : (cert.status||"NO DATA");
  document.getElementById("updated").textContent =
    report.generated_at || "No report / 보고서 없음";
  const summary=report.summary||{};
  const metrics=[
    ["Total / 전체",summary.total||0],
    ["BUY / 매수 후보",summary.buy_candidates||0],
    ["SELL / 매도 후보",summary.sell_candidates||0],
    ["HOLD / 보유 후보",summary.hold_candidates||0],
  ];
  document.getElementById("summary").innerHTML=metrics.map(([a,b])=>`
    <article class="metric"><span>${a}</span><strong>${b}</strong></article>
  `).join("");
  document.getElementById("candidates").innerHTML=(report.candidates||[]).map(c=>`
    <article class="candidate ${String(c.action).toLowerCase()}">
      <h3>${c.symbol} — ${c.action_i18n?.en||c.action} / ${c.action_i18n?.ko||""}</h3>
      <dl>
        <dt>Confidence / 신뢰도</dt><dd>${c.confidence}</dd>
        <dt>Score / 점수</dt><dd>${c.score}</dd>
        <dt>Regime / 시장 국면</dt><dd>${c.regime_i18n?.ko||c.regime}</dd>
        <dt>Trend / 추세</dt><dd>${c.trend_i18n?.ko||c.trend}</dd>
        <dt>Risk Gate / 리스크 게이트</dt><dd>${c.risk_gate}</dd>
      </dl>
      ${(c.reasons||[]).slice(0,3).map(r=>`
        <div class="reason">${r.en}<br>${r.ko}</div>
      `).join("")}
    </article>
  `).join("");
  document.getElementById("report").textContent=pretty(report);
}
async function refresh(){
  const r=await fetch("/api/dashboard",{cache:"no-store"});
  data=await r.json();render();
}
refresh();setInterval(refresh,5000);

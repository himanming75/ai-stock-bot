let data={};
function pretty(v){return JSON.stringify(v||{},null,2)}
function render(){
  const report=data.report||{};
  const cert=data.certification||{};
  document.getElementById("overall").textContent=
    cert.status==="PASS" ? "PASS / 통과" : (cert.status||"NO DATA");
  document.getElementById("updated").textContent=
    report.generated_at||"No report / 보고서 없음";

  const summary=report.summary||{};
  const bt=report.backtest_bridge||{};
  const metrics=[
    ["Candidates / 후보",summary.candidate_count||0],
    ["Top Buy / 최우선 매수",summary.top_buy_symbol||"-"],
    ["Top Sell / 최우선 매도",summary.top_sell_symbol||"-"],
    ["Avg AI Score / 평균 AI 점수",summary.average_ai_score||0],
    ["Win Rate / 승률",`${bt.win_rate_percent||0}%`],
    ["Max Drawdown / 최대 낙폭",`${bt.max_drawdown_percent||0}%`],
  ];
  document.getElementById("summary").innerHTML=metrics.map(([a,b])=>`
    <article class="metric"><span>${a}</span><strong>${b}</strong></article>
  `).join("");

  document.getElementById("ranking").innerHTML=(report.ranked_candidates||[]).map(c=>`
    <article class="candidate ${String(c.action).toLowerCase()}">
      <h3>#${c.rank} ${c.symbol} — ${c.action_i18n?.en||c.action} / ${c.action_i18n?.ko||""}</h3>
      <dl>
        <dt>AI Score / AI 점수</dt><dd>${c.ai_score}</dd>
        <dt>Confidence / 신뢰도</dt><dd>${c.ensemble_confidence}</dd>
        <dt>Position Size / 포지션 비율</dt><dd>${c.position_size_candidate?.suggested_position_percent||0}%</dd>
        <dt>Conflict Penalty / 충돌 패널티</dt><dd>${c.conflict_penalty}</dd>
      </dl>
      ${(c.explainability||[]).slice(0,3).map(r=>`
        <div class="reason">${r.en}<br>${r.ko}</div>
      `).join("")}
    </article>
  `).join("");

  document.getElementById("backtest").textContent=pretty(report.backtest_bridge);
  document.getElementById("safety").textContent=pretty(report.safety);
  document.getElementById("report").textContent=pretty(report);
}
async function refresh(){
  const r=await fetch("/api/dashboard",{cache:"no-store"});
  data=await r.json();render();
}
refresh();setInterval(refresh,5000);

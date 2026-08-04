const j=(v)=>JSON.stringify(v,null,2);
function metric(label,value,klass=""){return `<div class="card"><div class="label">${label}</div><div class="value ${klass}">${value}</div></div>`}
function table(el,rows){
  if(!rows||!rows.length){el.innerHTML="<tr><td>No data</td></tr>";return}
  const keys=Object.keys(rows[0]);
  el.innerHTML=`<thead><tr>${keys.map(k=>`<th>${k}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${keys.map(k=>`<td>${r[k]??""}</td>`).join("")}</tr>`).join("")}</tbody>`;
}
async function refresh(){
  const d=await fetch("/api/dashboard").then(r=>r.json());
  const stop=d.emergency_stop?.enabled;
  document.getElementById("statusBadge").textContent=stop?"STOPPED":"READY";
  document.getElementById("statusBadge").className="badge "+(stop?"bad":"ok");
  document.getElementById("metrics").innerHTML=[
    metric("Release",d.release.state,d.release.development_complete?"ok":"warn"),
    metric("Paper Equity",d.paper_account.equity??"N/A"),
    metric("Market",d.market_open===true?"OPEN":d.market_open===false?"CLOSED":"N/A",d.market_open?"ok":"warn"),
    metric("Risk Gate",d.risk.gate?.passed===true?"PASS":"BLOCKED",d.risk.gate?.passed?"ok":"warn"),
    metric("Cycle",d.orchestrator.state),
    metric("Live Orders",d.safety.actual_live_orders_submitted,d.safety.actual_live_orders_submitted===0?"ok":"bad")
  ].join("");
  document.getElementById("account").innerHTML=`<pre>${j(d.paper_account)}</pre>`;
  document.getElementById("risk").innerHTML=`<pre>${j(d.risk)}</pre>`;
  document.getElementById("cycle").innerHTML=`<pre>${j(d.orchestrator)}</pre>`;
  document.getElementById("stop").innerHTML=`<pre>${j(d.emergency_stop)}</pre>`;
  table(document.getElementById("positions"),d.paper_positions);
  table(document.getElementById("orders"),d.paper_orders);
  const logs=await fetch("/api/logs").then(r=>r.json());
  document.getElementById("logs").textContent=j(logs);
}
async function runAction(name){
  const r=await fetch("/api/action",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  const d=await r.json();
  document.getElementById("actionResult").textContent=j(d);
  await refresh();
}
async function setStop(enabled){
  const d=await fetch("/api/emergency-stop",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({enabled,reason:enabled?"WEB_EMERGENCY_STOP":"WEB_MANUAL_CLEAR"})}).then(r=>r.json());
  document.getElementById("actionResult").textContent=j(d);
  await refresh();
}
refresh();setInterval(refresh,15000);

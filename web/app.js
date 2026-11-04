const form = document.querySelector("#form");
const progress = document.querySelector("#progress");
const error = document.querySelector("#error");
const results = document.querySelector("#results");
const tokenInput = document.querySelector("#access-token");
const reviewerInput = document.querySelector("#reviewer-name");
let activeReport = null;
let activeEvents = [];

tokenInput.value = sessionStorage.getItem("datasheetdelta-access-token") || "";
tokenInput.addEventListener("change", () => sessionStorage.setItem("datasheetdelta-access-token", tokenInput.value.trim()));

for (const input of form.querySelectorAll('input[type="file"]')) {
  input.addEventListener("change", () => input.parentElement.querySelector("em").textContent = input.files[0]?.name || "Choose document");
}
const accessHeaders = () => tokenInput.value.trim() ? { Authorization: `Bearer ${tokenInput.value.trim()}` } : {};
const escapeHtml = value => String(value ?? "—").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

form.addEventListener("submit", async event => {
  event.preventDefault();
  error.hidden = true; results.hidden = true; progress.hidden = false;
  const submit = form.querySelector('button[type="submit"]'); submit.disabled = true;
  try {
    const response = await fetch("/api/investigations", {method:"POST",headers:accessHeaders(),body:new FormData(form)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Investigation failed.");
    activeReport = data; activeEvents = []; render();
    if (data.review_enabled && data.investigation_id) await loadReviewRecord();
  } catch (exception) {
    error.textContent = exception.message + " Check the access token, API service and document dependencies.";
    error.hidden = false;
  } finally { progress.hidden = true; submit.disabled = false; }
});

async function loadReviewRecord() {
  const response = await fetch(`/api/investigations/${encodeURIComponent(activeReport.investigation_id)}`,{headers:accessHeaders()});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Could not load review history.");
  activeEvents = data.review_events || [];
  activeReport.report_integrity_valid = data.report_integrity_valid;
  activeReport.review_chain_valid = data.review_chain_valid;
  render();
}

function render() {
  if (!activeReport) return;
  const report = activeReport, findings = report.findings || [], counts = {};
  findings.forEach(item => counts[item.status] = (counts[item.status] || 0) + 1);
  const order = ["changed","added","removed","unit_mismatch","ambiguous","unchanged"];
  const ordered = [...findings].sort((a,b) => order.indexOf(a.status)-order.indexOf(b.status) || a.parameter.localeCompare(b.parameter));
  const metrics = [["Compared",findings.length],["Changed",counts.changed||0],["Added",counts.added||0],["Removed",counts.removed||0],["Unit mismatch",counts.unit_mismatch||0],["Ambiguous",counts.ambiguous||0],["Unchanged",counts.unchanged||0]];
  const reviewEnabled = Boolean(report.review_enabled && report.investigation_id);
  results.innerHTML = `
    <div class="result-head"><div><p class="eyebrow">02 / INVESTIGATION RESULT</p><h2>Change register</h2>
    <p class="micro">${escapeHtml(report.reference_file)} → ${escapeHtml(report.revised_file)}</p>
    ${reviewEnabled ? `<p class="micro">Investigation ${escapeHtml(report.investigation_id)} · ${activeEvents.length} review events</p>` : ""}</div>
    <div class="actions"><button id="json" type="button">Export JSON</button><button id="csv" type="button">Export CSV</button></div></div>
    <div class="metrics">${metrics.map(([label,value]) => `<div class="metric"><b>${value}</b>${label}</div>`).join("")}</div>
    <div class="table-wrap"><table><thead><tr><th>PARAMETER</th><th>STATUS</th><th>REFERENCE</th><th>REVISED</th><th>REFERENCE EVIDENCE</th><th>REVISED EVIDENCE</th><th>INTERPRETATION</th>${reviewEnabled?"<th>HUMAN REVIEW</th>":""}</tr></thead>
    <tbody>${ordered.map(item => `<tr><td><b>${escapeHtml(item.parameter)}</b></td><td><span class="pill status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
    <td>${escapeHtml(item.reference)}</td><td>${escapeHtml(item.revised)}</td><td class="evidence">${escapeHtml(item.reference_source)}</td><td class="evidence">${escapeHtml(item.revised_source)}</td><td>${escapeHtml(item.explanation)}</td>
    ${reviewEnabled ? `<td class="review-cell"><select data-decision="${escapeHtml(item.parameter)}" aria-label="Review decision for ${escapeHtml(item.parameter)}"><option value="">Record decision</option><option value="confirmed_change">Confirmed change</option><option value="not_material">Not material</option><option value="needs_follow_up">Needs follow-up</option></select><textarea data-note="${escapeHtml(item.parameter)}" rows="2" maxlength="4000" placeholder="Reviewer note (optional)"></textarea><button type="button" data-save-review="${escapeHtml(item.parameter)}">Save review</button><div class="review-history">${renderHistory(item.parameter)}</div></td>`:""}</tr>`).join("")}</tbody></table></div>
    ${reviewEnabled ? `<div class="audit-state"><span>Report integrity: ${report.report_integrity_valid===false?"CHECK FAILED":"verified"}</span><span>Review chain: ${report.review_chain_valid===false?"CHECK FAILED":"verified"}</span><button id="delete-investigation" type="button" class="danger">Delete investigation and its review history</button></div>` : `<p class="micro">Persistent review history is disabled. Configure DATASHEETDELTA_ACCESS_TOKEN on the server and enter it above to enable saved investigations and review events.</p>`}
    ${(report.warnings||[]).map(message => `<p class="warning">${escapeHtml(message)}</p>`).join("")}
    <p class="micro">Extraction is not proof of completeness. Verify each result against the source documents. This tool does not certify safety, compliance or engineering suitability.</p>`;
  results.hidden = false;
  document.querySelector("#json").onclick = () => download("datasheetdelta.json",JSON.stringify({...report,review_events:activeEvents},null,2),"application/json");
  document.querySelector("#csv").onclick = () => download("datasheetdelta.csv",toCsv(report,activeEvents),"text/csv;charset=utf-8");
  for (const button of results.querySelectorAll("[data-save-review]")) button.addEventListener("click",()=>saveReview(button.dataset.saveReview,button));
  const deleteButton=document.querySelector("#delete-investigation");
  if(deleteButton) deleteButton.addEventListener("click",deleteInvestigation);
}

function renderHistory(parameter) {
  const events=activeEvents.filter(event=>event.parameter===parameter);
  if(!events.length) return '<span class="micro">No review recorded.</span>';
  return events.map(event=>`<p><b>${escapeHtml(event.decision.replaceAll("_"," "))}</b><br><span class="micro">${escapeHtml(event.reviewer)} · ${escapeHtml(event.created_at)}</span>${event.note?`<br>${escapeHtml(event.note)}`:""}</p>`).join("");
}

async function saveReview(parameter,button) {
  const decision=results.querySelector(`[data-decision="${CSS.escape(parameter)}"]`).value;
  const note=results.querySelector(`[data-note="${CSS.escape(parameter)}"]`).value;
  const reviewer=reviewerInput.value.trim();
  if(!decision){error.textContent="Choose a review decision first.";error.hidden=false;return;}
  if(!reviewer){error.textContent="Enter the reviewer name before recording a decision.";error.hidden=false;return;}
  button.disabled=true;
  try {
    const response=await fetch(`/api/investigations/${encodeURIComponent(activeReport.investigation_id)}/reviews`,{method:"POST",headers:{"Content-Type":"application/json",...accessHeaders()},body:JSON.stringify({parameter,decision,reviewer,note})});
    const data=await response.json(); if(!response.ok) throw new Error(data.detail||"Could not save review.");
    await loadReviewRecord();
  } catch(exception){error.textContent=exception.message;error.hidden=false;}
  finally{button.disabled=false;}
}

async function deleteInvestigation() {
  if(!confirm("Delete this investigation, its extracted report and all review history? This cannot be undone.")) return;
  const response=await fetch(`/api/investigations/${encodeURIComponent(activeReport.investigation_id)}`,{method:"DELETE",headers:accessHeaders()});
  const data=await response.json();
  if(!response.ok){error.textContent=data.detail||"Could not delete investigation.";error.hidden=false;return;}
  activeReport=null;activeEvents=[];results.hidden=true;error.textContent="Investigation and review history deleted.";error.hidden=false;
}

function toCsv(report,events) {
  const columns=["parameter","status","reference","revised","reference_source","revised_source","explanation","review_decision","reviewer","review_note","review_timestamp"];
  const latest=new Map(); for(const event of events) latest.set(event.parameter,event);
  const rows=[columns,...(report.findings||[]).map(item=>{const review=latest.get(item.parameter)||{};return [item.parameter,item.status,item.reference,item.revised,item.reference_source,item.revised_source,item.explanation,review.decision||"",review.reviewer||"",review.note||"",review.created_at||""];})];
  return rows.map(row=>row.map(value=>{const text=String(value??"");const safe=["=", "+", "-", "@"].includes(text.trimStart()[0])?"'"+text:text;return '"'+safe.replace(/"/g,'""')+'"';}).join(",")).join("\r\n");
}
function download(filename,body,type){const url=URL.createObjectURL(new Blob([body],{type}));const anchor=document.createElement("a");anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

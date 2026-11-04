const form = document.querySelector("#form");
const progress = document.querySelector("#progress");
const error = document.querySelector("#error");
const results = document.querySelector("#results");
let currentReport = null;
let review = {};

for (const input of form.querySelectorAll('input[type="file"]')) {
  input.addEventListener("change", () => {
    input.parentElement.querySelector("em").textContent = input.files[0]?.name || "Choose document";
  });
}

const esc = value => String(value ?? "—").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));

form.addEventListener("submit", async event => {
  event.preventDefault();
  error.hidden = true;
  results.hidden = true;
  progress.hidden = false;
  try {
    const response = await fetch("/api/investigations", { method: "POST", body: new FormData(form) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Investigation failed.");
    currentReport = payload;
    review = {};
    render(payload);
  } catch (exception) {
    error.textContent = exception.message + " Check the API service and optional document dependencies.";
    error.hidden = false;
  } finally {
    progress.hidden = true;
  }
});

function render(report) {
  const findings = report.findings || [];
  const counts = {};
  findings.forEach(item => counts[item.status] = (counts[item.status] || 0) + 1);
  results.innerHTML = `
    <div class="result-head">
      <div><p class="eyebrow">02 / INVESTIGATION RESULT</p><h2>Change register</h2>
      <p class="micro">${esc(report.reference_file)} → ${esc(report.revised_file)}</p></div>
      <div class="actions"><button id="export-review">Export reviewed package</button><button id="export-json">JSON</button><button id="export-csv">CSV</button></div>
    </div>
    <div class="metrics">${[["Compared",findings.length],["Changed",counts.changed||0],["Added",counts.added||0],["Removed",counts.removed||0],["Ambiguous",counts.ambiguous||0],["Unchanged",counts.unchanged||0]].map(([label,value])=>`<div class="metric"><b>${value}</b>${label}</div>`).join("")}</div>
    <div class="review-tools">
      <label>Filter <select id="status-filter"><option value="all">All findings</option><option value="changed">Changed</option><option value="added">Added</option><option value="removed">Removed</option><option value="ambiguous">Ambiguous</option><option value="unit_mismatch">Unit mismatch</option><option value="unchanged">Unchanged</option></select></label>
      <label>Find parameter <input id="search-filter" type="search" placeholder="Search names or values"></label>
      <span class="micro">Review decisions stay in this browser session until exported.</span>
    </div>
    <div id="finding-list" class="finding-list"></div>
    ${(report.warnings||[]).map(message=>`<p class="warning">${esc(message)}</p>`).join("")}
    <div class="limitations"><b>Interpretation boundary</b><p>A difference is not automatically a defect. Extraction may miss content outside supported structures. Verify each result against the source document. DatasheetDelta does not infer engineering impact, safety or compliance.</p></div>`;
  results.hidden = false;
  document.querySelector("#status-filter").addEventListener("change", drawFindings);
  document.querySelector("#search-filter").addEventListener("input", drawFindings);
  document.querySelector("#export-json").onclick = () => download("datasheetdelta.json", JSON.stringify(report, null, 2), "application/json");
  document.querySelector("#export-csv").onclick = () => download("datasheetdelta.csv", toCsv(report), "text/csv;charset=utf-8");
  document.querySelector("#export-review").onclick = () => {
    const packageData = {...report, human_review: findings.map(item => ({
      parameter: item.parameter,
      status: item.status,
      decision: review[item.parameter]?.decision || "not_reviewed",
      note: review[item.parameter]?.note || ""
    }))};
    download("datasheetdelta-reviewed-package.json", JSON.stringify(packageData, null, 2), "application/json");
  };
  drawFindings();
  results.scrollIntoView({behavior:"smooth", block:"start"});
}

function drawFindings() {
  const filter = document.querySelector("#status-filter").value;
  const query = document.querySelector("#search-filter").value.trim().toLowerCase();
  const selected = currentReport.findings.filter(item => {
    const matchesStatus = filter === "all" || item.status === filter;
    const searchable = [item.parameter,item.reference,item.revised,item.explanation].join(" ").toLowerCase();
    return matchesStatus && searchable.includes(query);
  });
  document.querySelector("#finding-list").innerHTML = selected.length ? selected.map((item,index) => {
    const state = review[item.parameter] || {};
    return `<article class="finding">
      <div class="finding-heading"><div><span class="pill ${esc(item.status)}">${esc(item.status.replace("_"," "))}</span><h3>${esc(item.parameter.replaceAll("_"," "))}</h3></div>
      <span class="micro">Finding ${index+1} / ${selected.length}</span></div>
      <div class="comparison"><div><small>REFERENCE</small><b>${esc(item.reference)}</b><p>${esc(item.reference_source)}</p></div><div><small>REVISED</small><b>${esc(item.revised)}</b><p>${esc(item.revised_source)}</p></div></div>
      <p class="explanation">${esc(item.explanation)}</p>
      <div class="review-fields"><label>Engineering review decision<select data-decision="${esc(item.parameter)}">
        <option value="not_reviewed" ${!state.decision||state.decision==="not_reviewed"?"selected":""}>Not reviewed</option>
        <option value="confirmed" ${state.decision==="confirmed"?"selected":""}>Confirmed against source</option>
        <option value="investigate" ${state.decision==="investigate"?"selected":""}>Requires investigation</option>
        <option value="not_applicable" ${state.decision==="not_applicable"?"selected":""}>Not applicable</option>
      </select></label><label>Reviewer note<textarea data-note="${esc(item.parameter)}" rows="2" placeholder="Record context or follow-up">${esc(state.note||"").replaceAll("—","")}</textarea></label></div>
    </article>`;
  }).join("") : '<p class="micro">No findings match this filter.</p>';
  document.querySelectorAll("[data-decision]").forEach(control => control.addEventListener("change", event => {
    const key = event.target.dataset.decision;
    review[key] = {...review[key], decision:event.target.value};
  }));
  document.querySelectorAll("[data-note]").forEach(control => control.addEventListener("input", event => {
    const key = event.target.dataset.note;
    review[key] = {...review[key], note:event.target.value};
  }));
}

function toCsv(report) {
  const columns = ["parameter","status","reference","revised","reference_source","revised_source","explanation"];
  const rows = [columns, ...report.findings.map(item => columns.map(column => item[column] ?? ""))];
  return rows.map(row => row.map(value => '"' + String(value).replace(/"/g,'""') + '"').join(",")).join("\r\n");
}

function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

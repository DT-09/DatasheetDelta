const form = document.querySelector("#form");
const progress = document.querySelector("#progress");
const error = document.querySelector("#error");
const results = document.querySelector("#results");

for (const input of form.querySelectorAll('input[type="file"]')) {
  input.addEventListener("change", () => {
    input.parentElement.querySelector("em").textContent =
      input.files[0]?.name || "Choose document";
  });
}

const escapeHtml = value => String(value ?? "—").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));

form.addEventListener("submit", async event => {
  event.preventDefault();
  error.hidden = true;
  results.hidden = true;
  progress.hidden = false;
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    const response = await fetch("/api/investigations", {
      method: "POST",
      body: new FormData(form)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Investigation failed.");
    render(data);
  } catch (exception) {
    error.textContent = exception.message +
      " Check that the API is running and document dependencies are installed.";
    error.hidden = false;
  } finally {
    progress.hidden = true;
    submit.disabled = false;
  }
});

function render(report) {
  const findings = report.findings || [];
  const counts = {};
  findings.forEach(item => counts[item.status] = (counts[item.status] || 0) + 1);
  const order = ["changed", "added", "removed", "unit_mismatch", "ambiguous", "unchanged"];
  const ordered = [...findings].sort((a, b) =>
    order.indexOf(a.status) - order.indexOf(b.status) ||
    a.parameter.localeCompare(b.parameter)
  );
  const metrics = [
    ["Compared", findings.length],
    ["Changed", counts.changed || 0],
    ["Added", counts.added || 0],
    ["Removed", counts.removed || 0],
    ["Unit mismatch", counts.unit_mismatch || 0],
    ["Ambiguous", counts.ambiguous || 0],
    ["Unchanged", counts.unchanged || 0]
  ];
  results.innerHTML = `
    <div class="result-head">
      <div><p class="eyebrow">02 / INVESTIGATION RESULT</p><h2>Change register</h2>
      <p class="micro">${escapeHtml(report.reference_file)} → ${escapeHtml(report.revised_file)}</p></div>
      <div class="actions"><button id="json" type="button">Export JSON</button><button id="csv" type="button">Export CSV</button></div>
    </div>
    <div class="metrics">${metrics.map(([label, value]) =>
      `<div class="metric"><b>${value}</b>${label}</div>`).join("")}</div>
    <div class="table-wrap"><table>
      <thead><tr><th>PARAMETER</th><th>STATUS</th><th>REFERENCE</th><th>REVISED</th>
      <th>REFERENCE EVIDENCE</th><th>REVISED EVIDENCE</th><th>INTERPRETATION</th></tr></thead>
      <tbody>${ordered.map(item => `<tr>
        <td><b>${escapeHtml(item.parameter)}</b></td>
        <td><span class="pill status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
        <td>${escapeHtml(item.reference)}</td><td>${escapeHtml(item.revised)}</td>
        <td class="evidence">${escapeHtml(item.reference_source)}</td>
        <td class="evidence">${escapeHtml(item.revised_source)}</td>
        <td>${escapeHtml(item.explanation)}</td>
      </tr>`).join("")}</tbody>
    </table></div>
    ${(report.warnings || []).map(message => `<p class="warning">${escapeHtml(message)}</p>`).join("")}
    <p class="micro">Extraction is not proof of completeness. Verify each result against the source documents. This tool does not certify safety, compliance or engineering suitability.</p>`;
  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
  document.querySelector("#json").onclick = () =>
    download("datasheetdelta.json", JSON.stringify(report, null, 2), "application/json");
  document.querySelector("#csv").onclick = () =>
    download("datasheetdelta.csv", toCsv(report), "text/csv;charset=utf-8");
}

function toCsv(report) {
  const columns = [
    "parameter", "status", "reference", "revised",
    "reference_source", "revised_source", "explanation"
  ];
  const rows = [columns, ...(report.findings || []).map(item => columns.map(key => item[key] ?? ""))];
  return rows.map(row => row.map(value =>
    '"' + String(value).replace(/"/g, '""') + '"'
  ).join(",")).join("\r\n");
}

function download(filename, body, type) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

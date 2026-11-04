const API_BASE = (window.DATASHEETDELTA_API || "https://datasheetdelta-api.onrender.com").replace(/\/$/, "");
const form=document.querySelector("#form"),progress=document.querySelector("#progress"),error=document.querySelector("#error"),results=document.querySelector("#results"),runButton=document.querySelector("#run-button"),apiIndicator=document.querySelector("#api-indicator");
const esc=value=>String(value??"—").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
for(const input of form.querySelectorAll('input[type="file"]')){
  input.addEventListener("change",()=>{const file=input.files[0];const label=document.querySelector("#"+input.name+"-label");label.innerHTML=file?esc(file.name)+" <span>✓</span>":"Choose a file <span>＋</span>";});
}
async function checkService(){
  try{const response=await fetch(API_BASE+"/api/health",{headers:{Accept:"application/json"}});if(!response.ok)throw new Error("Service returned "+response.status);const data=await response.json();apiIndicator.className="api-indicator online";apiIndicator.innerHTML="<i></i><span>Analysis service online · v"+esc(data.version||"")+"</span>";}
  catch{apiIndicator.className="api-indicator offline";apiIndicator.innerHTML="<i></i><span>Analysis service not connected</span>";}
}
checkService();
form.addEventListener("submit",async event=>{
  event.preventDefault();error.hidden=true;results.hidden=true;progress.hidden=false;runButton.disabled=true;runButton.innerHTML="Investigating <span>…</span>";
  try{
    const response=await fetch(API_BASE+"/api/investigations",{method:"POST",body:new FormData(form)});
    const data=await response.json().catch(()=>({detail:"The analysis service returned an unreadable response."}));
    if(!response.ok)throw new Error(data.detail||"Investigation failed.");
    render(data);
  }catch(exception){
    const offline=exception instanceof TypeError;
    error.innerHTML="<b>"+(offline?"Analysis service unavailable.":"Investigation could not be completed.")+"</b><br>"+esc(exception.message)+(offline?"<br><small>The website is live, but its Python analysis service must be deployed and reachable. See the repository deployment guide.</small>":"");
    error.hidden=false;
  }finally{progress.hidden=true;runButton.disabled=false;runButton.innerHTML='Run investigation <span>↗</span>';checkService();}
});
document.querySelector("#load-sample").addEventListener("click",()=>render(sampleReport(),true));
function sampleReport(){return {reference_file:"pump-assembly-rev-A.csv",revised_file:"pump-assembly-rev-B.csv",summary:{total:6,changed:2,added:1,removed:1,unchanged:1,unit_mismatch:1,review_required:true},warnings:["Illustrative sample only. These values are synthetic and are not customer data or a validation result."],findings:[
{parameter:"maximum_pressure",status:"changed",reference:"10 bar",revised:"12 bar",reference_source:"row 4",revised_source:"row 4",explanation:"Compared in Pa; tolerance is 0 Pa."},
{parameter:"rated_voltage",status:"unchanged",reference:"24 V DC",revised:"24 V DC",reference_source:"row 7",revised_source:"row 7",explanation:"Extracted values are identical."},
{parameter:"ingress_protection",status:"changed",reference:"IP 65",revised:"IP 67",reference_source:"row 9",revised_source:"row 9",explanation:"Text or value differs; assess engineering materiality."},
{parameter:"operating_temperature",status:"unit_mismatch",reference:"80 °C",revised:"176 °F",reference_source:"row 12",revised_source:"row 12",explanation:"Units are unknown or not comparable; manual review required."},
{parameter:"sensor_output",status:"added",reference:null,revised:"4–20 mA",reference_source:null,revised_source:"row 15",explanation:"Field appears only in revised document."},
{parameter:"housing_material",status:"removed",reference:"Aluminium",revised:null,reference_source:"row 17",revised_source:null,explanation:"Field appears only in reference document."}
]};}
function render(report,isSample=false){
  const findings=report.findings||[],counts=report.summary||{};
  const metrics=[["TOTAL FIELDS",counts.total??findings.length],["CHANGED",counts.changed??0],["ADDED",counts.added??0],["REMOVED",counts.removed??0],["UNCHANGED",counts.unchanged??0],["UNIT REVIEW",counts.unit_mismatch??0]];
  results.innerHTML='<div class="result-head"><div><div class="section-kicker">'+(isSample?"ILLUSTRATIVE SAMPLE":"INVESTIGATION RESULT")+'</div><h3>Change register</h3><div class="result-meta">'+esc(report.reference_file)+' → '+esc(report.revised_file)+'</div></div><div class="result-actions"><button class="small-button" id="export-json">Export JSON ↓</button><button class="small-button" id="export-csv">Export CSV ↓</button></div></div>'+
  '<div class="metrics">'+metrics.map(([label,value])=>'<div class="metric"><b>'+esc(value)+'</b><span>'+label+'</span></div>').join("")+'</div>'+
  '<div class="register-tools"><label>SEARCH FINDINGS<input id="search" type="search" placeholder="Parameter or source…"></label><label>FILTER BY STATUS<select id="status"><option value="all">All findings</option><option value="changed">Changed</option><option value="added">Added</option><option value="removed">Removed</option><option value="unchanged">Unchanged</option><option value="unit_mismatch">Unit mismatch</option></select></label><span id="visible-count"></span></div>'+
  '<div class="table-wrap"><table><thead><tr><th>PARAMETER</th><th>STATUS</th><th>REFERENCE VALUE</th><th>REVISED VALUE</th><th>REFERENCE SOURCE</th><th>REVISED SOURCE</th><th>COMPARISON NOTE</th></tr></thead><tbody id="finding-rows"></tbody></table></div>'+
  (report.warnings||[]).map(w=>'<p class="warning">'+esc(w)+'</p>').join("")+
  '<p class="review-note">Review required. Extraction is not proof of completeness. Confirm every finding against the original documents. No safety, compliance or engineering suitability conclusion is made.</p>';
  const search=document.querySelector("#search"),status=document.querySelector("#status"),tbody=document.querySelector("#finding-rows"),visibleCount=document.querySelector("#visible-count");
  function drawRows(){const term=search.value.trim().toLowerCase(),selected=status.value;const visible=findings.filter(item=>(selected==="all"||item.status===selected)&&[item.parameter,item.reference,item.revised,item.reference_source,item.revised_source,item.explanation].join(" ").toLowerCase().includes(term));tbody.innerHTML=visible.map(item=>'<tr><td><b>'+esc(item.parameter)+'</b></td><td><span class="pill status-'+esc(item.status)+'">'+esc((item.status||"").replace("_"," "))+'</span></td><td>'+esc(item.reference)+'</td><td>'+esc(item.revised)+'</td><td class="evidence">'+esc(item.reference_source)+'</td><td class="evidence">'+esc(item.revised_source)+'</td><td>'+esc(item.explanation)+'</td></tr>').join("");if(!visible.length)tbody.innerHTML='<tr><td colspan="7" class="empty-state">No findings match this filter.</td></tr>';visibleCount.textContent="SHOWING "+visible.length+" / "+findings.length;}
  search.addEventListener("input",drawRows);status.addEventListener("change",drawRows);drawRows();results.hidden=false;
  document.querySelector("#export-json").onclick=()=>download("datasheetdelta-investigation.json",JSON.stringify(report,null,2),"application/json");
  document.querySelector("#export-csv").onclick=()=>download("datasheetdelta-change-register.csv",toCsv(findings),"text/csv;charset=utf-8");
  results.scrollIntoView({behavior:"smooth",block:"start"});
}
function toCsv(findings){const columns=["parameter","status","reference","revised","reference_source","revised_source","explanation"];return [columns,...findings.map(item=>columns.map(key=>item[key]??""))].map(row=>row.map(value=>'"'+String(value).replace(/"/g,'""')+'"').join(",")).join("\r\n");}
function download(filename,body,type){const url=URL.createObjectURL(new Blob([body],{type}));const anchor=document.createElement("a");anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

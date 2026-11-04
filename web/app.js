const form=document.querySelector('#form');
const progress=document.querySelector('#progress');
const error=document.querySelector('#error');
const results=document.querySelector('#results');
for(const input of form.querySelectorAll('input[type=file]')){
  input.addEventListener('change',()=>input.parentElement.querySelector('em').textContent=input.files[0]?.name||'Choose document');
}
const esc=value=>String(value??'—').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
form.addEventListener('submit',async event=>{
  event.preventDefault(); error.hidden=true; results.hidden=true; progress.hidden=false;
  try{
    const response=await fetch('/api/investigations',{method:'POST',body:new FormData(form)});
    const data=await response.json();
    if(!response.ok)throw Error(data.detail||'Investigation failed');
    render(data);
  }catch(exception){
    error.textContent=exception.message+' — check that the API is running and document dependencies are installed.';
    error.hidden=false;
  }finally{progress.hidden=true;}
});
function render(report){
  const findings=report.findings||[];
  const counts=report.summary||{};
  const metrics=[['Compared',counts.total??findings.length],['Changed',counts.changed??0],
    ['Added',counts.added??0],['Removed',counts.removed??0],['Unchanged',counts.unchanged??0],
    ['Unit review',counts.unit_mismatch??0]];
  results.innerHTML=
    '<div class="result-head"><div><p class="eyebrow">02 / INVESTIGATION RESULT</p><h2>Change register</h2><p class="micro">'+esc(report.reference_file)+' → '+esc(report.revised_file)+'</p></div>'+
    '<div class="actions"><button id="json">Export JSON</button><button id="csv">Export CSV</button></div></div>'+
    '<div class="metrics">'+metrics.map(([label,value])=>'<div class="metric"><b>'+value+'</b>'+label+'</div>').join('')+'</div>'+
    '<div class="register-tools"><label>Find a parameter <input id="search" type="search" placeholder="Search field or source"></label>'+
    '<label>Show status <select id="status"><option value="all">All findings</option><option>changed</option><option>added</option><option>removed</option><option>unchanged</option><option value="unit_mismatch">unit mismatch</option></select></label>'+
    '<span id="visible-count" class="micro"></span></div>'+
    '<div class="table-wrap"><table><thead><tr><th>FIELD</th><th>STATUS</th><th>REFERENCE</th><th>REVISED</th><th>REFERENCE SOURCE</th><th>REVISED SOURCE</th><th>EXPLANATION</th></tr></thead><tbody id="finding-rows"></tbody></table></div>'+
    (report.warnings||[]).map(warning=>'<p class="warning">'+esc(warning)+'</p>').join('')+
    '<p class="review-note">Extraction is not proof of completeness. Verify every finding against the source documents. This tool does not certify safety, compliance or engineering suitability.</p>';
  const search=document.querySelector('#search'),status=document.querySelector('#status');
  const tbody=document.querySelector('#finding-rows'),visibleCount=document.querySelector('#visible-count');
  function drawRows(){
    const term=search.value.trim().toLowerCase(),selected=status.value;
    const visible=findings.filter(item=>{
      const matchesStatus=selected==='all'||item.status===selected;
      const haystack=[item.parameter,item.reference,item.revised,item.reference_source,item.revised_source,item.explanation].join(' ').toLowerCase();
      return matchesStatus&&haystack.includes(term);
    });
    tbody.innerHTML=visible.map(item=>'<tr><td><b>'+esc(item.parameter)+'</b></td>'+
      '<td><span class="pill status-'+esc(item.status)+'">'+esc(item.status.replace('_',' '))+'</span></td>'+
      '<td>'+esc(item.reference)+'</td><td>'+esc(item.revised)+'</td>'+
      '<td class="evidence">'+esc(item.reference_source)+'</td><td class="evidence">'+esc(item.revised_source)+'</td>'+
      '<td>'+esc(item.explanation)+'</td></tr>').join('');
    if(!visible.length)tbody.innerHTML='<tr><td colspan="7" class="empty-state">No findings match this filter.</td></tr>';
    visibleCount.textContent='Showing '+visible.length+' of '+findings.length+' fields';
  }
  search.addEventListener('input',drawRows); status.addEventListener('change',drawRows); drawRows();
  results.hidden=false;
  document.querySelector('#json').onclick=()=>download('datasheetdelta.json',JSON.stringify(report,null,2),'application/json');
  document.querySelector('#csv').onclick=()=>download('datasheetdelta.csv',toCsv(findings),'text/csv');
  results.scrollIntoView({behavior:'smooth',block:'start'});
}
function toCsv(findings){
  const columns=['parameter','status','reference','revised','reference_source','revised_source','explanation'];
  return [columns,...findings.map(item=>columns.map(key=>item[key]??''))]
    .map(row=>row.map(value=>'"'+String(value).replace(/"/g,'""')+'"').join(',')).join('\r\n');
}
function download(filename,body,type){
  const url=URL.createObjectURL(new Blob([body],{type}));
  const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

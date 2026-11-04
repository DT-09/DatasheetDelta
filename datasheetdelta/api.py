from pathlib import Path
from fastapi import FastAPI,File,Form,HTTPException,UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from .core import extract,compare,report_csv
import json
app=FastAPI(title="DatasheetDelta",version="0.1.0")
@app.get("/api/health")
def health(): return {"status":"ok","product":"DatasheetDelta"}
async def read_doc(file):
 name=file.filename or "document"; ext=Path(name).suffix.lower()
 if ext not in {".csv",".xlsx",".docx",".pdf",".txt",".md"}: raise HTTPException(415,"Unsupported document format")
 data=await file.read(15*1024*1024+1)
 if not data: raise HTTPException(400,"Empty document")
 if len(data)>15*1024*1024: raise HTTPException(413,"Maximum file size is 15 MB")
 try: return name,*extract(name,data)
 except ValueError as e: raise HTTPException(422,str(e)) from e
@app.post("/api/investigations")
async def investigate(reference:UploadFile=File(...),revised:UploadFile=File(...),tolerance:float=Form(0)):
 if tolerance<0: raise HTTPException(422,"Tolerance must be non-negative")
 an,af,aw=await read_doc(reference); bn,bf,bw=await read_doc(revised); result=compare(an,af,bn,bf,tolerance); result["warnings"]=aw+bw; return result
@app.post("/api/reports/{kind}")
async def export(kind:str,reference:UploadFile=File(...),revised:UploadFile=File(...),tolerance:float=Form(0)):
 if kind not in {"json","csv"}: raise HTTPException(404,"Use json or csv")
 an,af,aw=await read_doc(reference); bn,bf,bw=await read_doc(revised); result=compare(an,af,bn,bf,tolerance); result["warnings"]=aw+bw
 body=json.dumps(result,indent=2) if kind=="json" else report_csv(result)
 return Response(body,media_type="application/json" if kind=="json" else "text/csv",headers={"Content-Disposition":f"attachment; filename=datasheetdelta.{kind}"})

app.mount('/', StaticFiles(directory='web', html=True), name='web')

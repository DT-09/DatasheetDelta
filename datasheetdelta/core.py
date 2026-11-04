from __future__ import annotations
import csv, io, re
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class Field:
    name: str
    value: str
    number: float | None
    unit: str | None
    source: str
    excerpt: str

@dataclass
class Finding:
    parameter: str
    status: str
    reference: str | None
    revised: str | None
    reference_source: str | None
    revised_source: str | None
    explanation: str

ALIASES={"max pressure":"maximum_pressure","maximum pressure":"maximum_pressure","operating pressure":"operating_pressure","rated voltage":"rated_voltage","max temperature":"maximum_temperature","maximum temperature":"maximum_temperature","operating temperature":"operating_temperature","ip rating":"ingress_protection"}
FACTORS={"mm":("length",1),"cm":("length",10),"m":("length",1000),"in":("length",25.4),"inch":("length",25.4),"pa":("pressure",1),"kpa":("pressure",1000),"mpa":("pressure",1000000),"bar":("pressure",100000),"psi":("pressure",6894.757293),"v":("voltage",1),"mv":("voltage",.001),"kv":("voltage",1000),"a":("current",1),"ma":("current",.001),"w":("power",1),"kw":("power",1000),"hz":("frequency",1),"khz":("frequency",1000),"mhz":("frequency",1000000),"kg":("mass",1),"g":("mass",.001),"°c":("temperature",1),"c":("temperature",1),"%":("percentage",1)}
NUM=re.compile(r"^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?)\s*([A-Za-z°%µμ/²³._-]+)?\s*$")
def _field(label,value,source,excerpt):
    label=re.sub(r"\s+"," ",label.strip().lower()).rstrip(":")
    if not label or not value.strip(): return None
    name=ALIASES.get(label,re.sub(r"[^a-z0-9]+","_",label).strip("_"))
    value=value.strip(); m=NUM.match(value)
    if m and m.group(1):
        n=float(m.group(1).replace(",","")); unit=m.group(2); factor=FACTORS.get((unit or "").lower())
        if factor: return Field(name,value,n*factor[1],unit,source,excerpt)
        return Field(name,value,n,unit,source,excerpt)
    return Field(name,value,None,None,source,excerpt)
def extract(filename:str,content:bytes):
    ext=Path(filename).suffix.lower(); fields=[]; warnings=[]
    def add(label,value,loc,line):
        f=_field(str(label or ""),str(value or ""),loc,line)
        if f: fields.append(f)
    if ext==".csv":
        text=content.decode("utf-8-sig"); rows=csv.reader(io.StringIO(text))
        for i,row in enumerate(rows,1):
            if len(row)>=2: add(row[0],row[1],f"row {i}",f"{row[0]}: {row[1]}")
    elif ext in {".txt",".md"}:
        for i,line in enumerate(content.decode("utf-8-sig").splitlines(),1):
            if ":" in line:
                a,b=line.split(":",1); add(a,b,f"line {i}",line)
    elif ext==".xlsx":
        try: import openpyxl
        except ImportError as e: raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from e
        wb=openpyxl.load_workbook(io.BytesIO(content),data_only=True,read_only=True)
        for ws in wb.worksheets:
            for i,row in enumerate(ws.iter_rows(values_only=True),1):
                if len(row)>=2: add(row[0],row[1],f"{ws.title}!row {i}",f"{row[0]}: {row[1]}")
    elif ext==".docx":
        try: from docx import Document
        except ImportError as e: raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from e
        doc=Document(io.BytesIO(content))
        for ti,table in enumerate(doc.tables,1):
            for ri,row in enumerate(table.rows,1):
                if len(row.cells)>=2: add(row.cells[0].text,row.cells[1].text,f"table {ti}, row {ri}",f"{row.cells[0].text}: {row.cells[1].text}")
        for i,p in enumerate(doc.paragraphs,1):
            if ":" in p.text:
                a,b=p.text.split(":",1); add(a,b,f"paragraph {i}",p.text)
    elif ext==".pdf":
        try: from pypdf import PdfReader
        except ImportError as e: raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from e
        reader=PdfReader(io.BytesIO(content))
        for pi,page in enumerate(reader.pages,1):
            for li,line in enumerate((page.extract_text() or "").splitlines(),1):
                if ":" in line:
                    a,b=line.split(":",1); add(a,b,f"page {pi}, line {li}",line)
        if not fields: warnings.append("No text fields found. Scanned PDFs need OCR; OCR is not included.")
    else: raise ValueError("Supported formats: CSV, XLSX, DOCX, text PDF, TXT and MD.")
    unique={}
    for f in fields: unique.setdefault(f.name,f)
    if not unique: warnings.append(f"No label/value fields extracted from {filename}. Use a two-column table or Label: value lines.")
    return list(unique.values()),warnings
def compare(reference_name,old,revised_name,new,tolerance=0):
    if tolerance<0: raise ValueError("Tolerance must be non-negative")
    a={x.name:x for x in old}; b={x.name:x for x in new}; out=[]
    for key in sorted(a.keys()|b.keys()):
        x=a.get(key); y=b.get(key)
        if x is None: status="added"; why="Field appears only in revised document."
        elif y is None: status="removed"; why="Field appears only in reference document."
        elif x.value==y.value: status="unchanged"; why="Extracted values are identical."
        elif x.number is not None and y.number is not None and x.unit and y.unit:
            dx=FACTORS.get(x.unit.lower()); dy=FACTORS.get(y.unit.lower())
            if dx and dy and dx[0]==dy[0]:
                status="unchanged" if abs(x.number-y.number)<=tolerance else "changed"; why="Values compared in common base units."
            elif x.unit.lower()!=y.unit.lower(): status="unit_mismatch"; why="Units could not be safely normalized; manual review required."
            else: status="changed"; why="Numeric value differs."
        else: status="changed"; why="Text or value differs; assess materiality."
        out.append(Finding(key,status,x.value if x else None,y.value if y else None,x.source if x else None,y.source if y else None,why))
    return {"reference_file":reference_name,"revised_file":revised_name,"findings":[asdict(x) for x in out],"warnings":[],"review_required":True,"method":"deterministic label/value comparison"}
def report_csv(result):
    s=io.StringIO(); w=csv.writer(s); w.writerow(["parameter","status","reference","revised","reference_source","revised_source","explanation"])
    for f in result["findings"]: w.writerow([f[k] for k in ["parameter","status","reference","revised","reference_source","revised_source","explanation"]])
    return s.getvalue()

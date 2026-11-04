import argparse,json
from pathlib import Path
from .core import extract,compare,report_csv

def main():
 p=argparse.ArgumentParser(description="Compare engineering specification revisions"); p.add_argument("reference"); p.add_argument("revised"); p.add_argument("--out",default="datasheetdelta-report"); a=p.parse_args()
 x=Path(a.reference); y=Path(a.revised); old,w1=extract(x.name,x.read_bytes()); new,w2=extract(y.name,y.read_bytes()); result=compare(x.name,old,y.name,new); result["warnings"]=w1+w2
 base=Path(a.out); base.parent.mkdir(parents=True,exist_ok=True); base.with_suffix(".json").write_text(json.dumps(result,indent=2)); base.with_suffix(".csv").write_text(report_csv(result)); print(f"Compared {len(result['findings'])} fields; reports saved with prefix {base}.")
if __name__=="__main__": main()

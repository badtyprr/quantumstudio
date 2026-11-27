"""Check IBM-081's matrix and scalar limits and their physical time scale."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("windows",type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report",type=Path)
reports.add_argument("--session-report",type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
source = json.loads(Path(__file__).with_name("ibm081-inventory.json").read_bytes())
cases = {}

def check(name,expr,expected):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,
                            check=True,capture_output=True,timeout=30)
    value=json.loads(result.stdout)
    assert not value["approximate"] and value["copy_text"]==expected,(name,value["copy_text"])
    cases[name] = expr,expected

_,matrix,initial = source["rows"][218]["literal"].strip("$ \n.").split("=")
check("matrix-at-zero","$"+matrix+"$","matrix(2,2,[1 ∕ 2,1 ∕ 2,1 ∕ 2,1 ∕ 2])")
check("initial-density","$"+matrix+"="+initial+"$","1")
final = matrix.replace(r"\rightarrow 0",r"\rightarrow 1")
check("matrix-at-one","$"+final+"$","matrix(2,2,[1,0,0,0])")
check("different-endpoints","$"+final+"="+initial+"$","0")

chain = source["rows"][225]["literal"]
for time in ("1","2","(1/4)"):
    check("time-scale-"+str(len(cases)),chain.replace("T_1",time),"1")
check("scalar-at-one","$"+chain.strip("$ \n").split("=")[0]+"$","0")
for name,expr,expected in [
    ("right",r"\lim_{x\to0^+}{\frac{|x|}{x}}","1"),
    ("left",r"\lim_{x\to0^{-}}{\frac{|x|}{x}}","−1"),
    ("removable",r"\lim_{x\to0}\frac{\sin{x}}{x}","1"),
    ("ungrouped",r"\lim_{x\to2}x^2+3","7"),
    ("nested",r"\lim_{p\to1}{\lim_{p\to0}{p}+p}","1"),
    ("outer-point",r"\lim_{x\to3}{\lim_{p\to x}{p+1}}","4"),
]:
    check(name,"$"+expr+"$",expected)
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,14,
                 dict(source_sha256=source["source_sha256"],source_rows=[219,226]),
                 sessions_only=bool(args.session_report))

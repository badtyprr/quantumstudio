"""Replay the relaxation and dephasing exercises using the printed Kraus matrices."""
import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import subprocess

from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report", type=Path)
reports.add_argument("--session-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm081-inventory.json").read_bytes())
cases = {}

def evaluate(expr):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),
                          capture_output=True,timeout=30,env=env,check=True)
    result = json.loads(proc.stdout)
    assert not result["approximate"],expr
    return result["copy_text"]

def check(name,expr,expected):
    assert evaluate(expr)==expected,(name,expected)
    cases[name] = expr,expected

for number in (214,238):
    row = inventory["rows"][number-1]
    matrices = re.findall(r"\\begin\{pmatrix\}.*?\\end\{pmatrix\}",row["literal"],re.S)
    assert row["cell"]==39 and len(matrices)==2
    for prob in map(Fraction,["0","1/4","1/2","3/4","1"]):
        key = f"{row['id']}-{prob.numerator}-{prob.denominator}"
        operators = []
        for i,matrix in enumerate(matrices):
            literal = "$"+re.sub(r"\bp\b",str(prob),matrix)+"$"
            copy = evaluate(literal)
            assert evaluate(copy)==copy
            cases[f"{key}-A{i}"] = literal,copy
            operators.append("("+copy+")")
        a,b = operators
        check(key+"-complete",f"{a}~*{a}+{b}~*{b}==I","1")
        check(key+"-omit-A1",f"{a}~*{a}==I",str(int(prob==0)))
        if number==214:
            state = "([1,1;1,1]/2)"
            expected = f"([{1+prob},sqrt({1-prob});sqrt({1-prob}),{1-prob}]/2)"
        else:
            state = "([16,12i;-12i,9]/25)"
            coherence = 12*(1-2*prob)
            expected = f"([16,({coherence})*i;({-coherence})*i,9]/25)"
        check(key+"-output",f"{a}*{state}*{a}~+{b}*{state}*{b}~=={expected}","1")

clipboard_checks(worker,args.windows,args.report or args.session_report,cases,50,
                 dict(source_sha256=inventory["source_sha256"],matrix_source_rows=[214,238]),
                 sessions_only=bool(args.session_report))

"""Check two independent outcome alphabets against a rectangular state table."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
cases = {}
sources = {}

def evaluate(expr):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,timeout=30)
    assert proc.returncode == 0, (expr,proc.stderr)
    result = json.loads(proc.stdout)
    assert not result["approximate"]
    return result["copy_text"]

def bind(expr,pairs):
    for key,value in pairs:
        expr = f'replace(({expr}),"{key}",{value})'
    return expr

def check(name,expr,expected):
    actual = evaluate(expr)
    assert actual == expected,(name,actual,expected)
    cases[name] = expr,expected

domains = [("Σ","qset(vector(0,1))"),("Γ","qset(vector(0,1,2))")]
fields = [f"{i}_{j}" for i in range(2) for j in range(3)]
probability = ["1/21","2/21","3/21","4/21","5/21","6/21"]
amplitude = ["0","0","i*3/5","0","4/5","0"]
for lesson, numbers in (("041",(91,131,229)),("042",(31,104,106,166,168,169,170))):
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    sources[lesson] = inventory["source_sha256"]
    for n in numbers:
        row = inventory["rows"][n-1]
        copied = evaluate(row["literal"])
        assert evaluate(copied)==copied, row["id"]
        cases[row["id"]] = row["literal"],copied
        values = probability if n in (91,229,166,168) else amplitude
        family = "p" if values is probability else "α"
        assignments = [(family+"_"+field,value) for field,value in zip(fields,values)]
        column = "["+";".join(values)+"]"
        if n==31:
            check(row["id"]+"-factors",bind(copied,[("φ","[0;i]"),("ψ","[1;0;0]")]+domains),"1")
            deferred = evaluate(bind(copied,domains))
            check(row["id"]+"-domains-first",bind(copied,domains),deferred)
            check(row["id"]+"-deferred-copy",deferred,deferred)
            states = [("φ","[0;2*i]"),("ψ","[1;0;1]")]
            check(row["id"]+"-scaled",bind(deferred,states),"1")
            # Change only the last equality. Nonunit factors distinguish
            # computing the norms from assuming every named state is a unit.
            left,marker,right = row["literal"].rpartition("& =")
            assert marker
            wrong = evaluate(left+marker+"2 "+right)
            check(row["id"]+"-wrong-norm",bind(evaluate(bind(wrong,domains)),states),"0")
            continue
        concrete = evaluate(bind(copied,domains))
        if n in (91,166):
            check(row["id"]+"-table","norm(("+bind(concrete,assignments)+")-"+column+")","0")
        elif n in (104,169,229):
            name = "pi" if n==229 else "ψ"
            check(row["id"]+"-match",bind(concrete,assignments+[(name,column)]),"1")
            check(row["id"]+"-reverse",bind(concrete,assignments+[(name,"["+";".join(reversed(values))+"]")]),"0")
        elif n==131:
            factors = [("φ","[0;i]"),("ψ","[1;0;0]")]
            factors += [("α_0","0"),("α_1","i"),("β_0","1"),("β_1","0"),("β_2","0")]
            check(row["id"]+"-factors",bind(concrete,factors),"1")
        elif n==106:
            check(row["id"]+"-unit",bind(concrete,assignments),"1")
            check(row["id"]+"-scaled",bind(concrete,[(key,"2*("+val+")") for key,val in assignments]),"0")
        elif n==168:
            check(row["id"]+"-equivalent",bind(copied,domains),"1")
        else:
            check(row["id"]+"-marginal","norm(("+bind(concrete,assignments)+")-[3*i/5;4/5])","0")

sparse = evaluate(r"$\sum_{(a,b)\in\Sigma\times\Gamma}{10a+b}$")
check("nonconsecutive",bind(sparse,[("Σ","qset(vector(3,5))"),("Γ","qset(vector(2,7,8))")]),"274")
check("empty",bind(sparse,[("Σ","qset(vector())"),domains[1]]),"0")
clipboard_checks(worker,args.windows,args.report,cases,30,dict(source_sha256=sources))

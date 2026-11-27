"""Check the five-system state and measurement in the original suit notation."""
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
inventory = json.loads(Path(__file__).with_name("ibm042-inventory.json").read_bytes())
cases = {}

def evaluate(expr):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),
                            capture_output=True,env=env,timeout=30)
    assert result.returncode==0,result.stderr
    data = json.loads(result.stdout)
    assert not data["approximate"]
    return data["copy_text"]

def check(key,expr,expected):
    actual = evaluate(expr)
    assert actual==expected,(key,actual[:140],expected[:140])
    cases[key] = expr,expected

def bind(expr):
    for index,suit in enumerate("♣♢♡♠"):
        expr = f'replace(({expr}),"{suit}",qbasis({index},4))'
    return expr

# Derive the index in the joint basis independently, in register order 4..0.
terms = [("20133","sqrt(1/7)"),("10130","sqrt(2/7)"),("33010","sqrt(1/7)"),
         ("20122","-i*sqrt(2/7)"),("32030","-sqrt(1/7)")]
expected = "+".join(f"({amplitude})*qbasis({int(digits,4)},1024)" for digits,amplitude in terms)
for number in (173,174,179,191,193,195,197):
    row = inventory["rows"][number-1]
    literal = row["literal"]
    copied = evaluate(literal)
    assert evaluate(copied)==copied,row["id"]
    cases[row["id"]] = literal,copied
    if number in (173,174):
        check(f"full-state-{number}","norm(("+bind(copied)+")-("+expected+"))","0")
    else:
        check(f"identity-{number}",bind(copied),"1")
    if number in (191,193,195):
        left,_,_ = literal.strip("$ \r\n.").partition("=")
        probability = {"191":"3/7","193":"2/7","195":"2/7"}[str(number)]
        check(f"probability-{number}",bind(evaluate("$$"+left+"$$")),evaluate(probability))
        check(f"wrong-probability-{number}",bind(evaluate("$$"+left+"=1/7$$")),"0")
    if number==197:
        before,marker,after = literal.rpartition("=")
        assert marker and "-i" in after
        wrong = evaluate(before+marker+after.replace("-i","+i",1))
        check("wrong-conditional-phase",bind(wrong),"0")

clipboard_checks(worker,args.windows,args.report,cases,21,dict(source_sha256=inventory["source_sha256"]))

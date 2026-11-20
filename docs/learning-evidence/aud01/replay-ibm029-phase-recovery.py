"""Check phase recovery against exhaustive reduced fractions and the pinned IBM-029 fact."""
import argparse
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("gui", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
source = {n: inventory["rows"][n-1] for n in (218,277,278,279,280,281,282)}
inputs = [[r["id"],r["literal"],"0"] for r in source.values()]
examples = [("coarse", "3/16",21,"3/16"), ("fine","171/1024",21,"1/6"),
            ("exact","1/6",21,"1/6"), ("no-match","1/8",2,None),
            ("zero","1/9",2,"0"), ("one","8/9",2,"1"),
            ("irrational","sqrt(2)/2",8,"5/7"), ("pi","pi/4",15,"11/14"),
            ("irrational-no-match","sqrt(2)-1",18,None)]
for label, phase, bound, _ in examples:
    inputs.append(["fraction-"+label,f"recoverphase({phase},{bound})","0"])
inputs.append(["fraction-unbound","recoverphase(α,N)","0"])
if not args.report:
    args.gui.mkdir(exist_ok=True,parents=True)
    (args.gui/"inputs.json").write_bytes(json.dumps(inputs,ensure_ascii=False).encode())
    raise SystemExit()


@lru_cache(maxsize=2048)
def evaluate(text):
    return subprocess.run([worker,"--json"],input=("quantum:"+text).encode(),env=env,
                          timeout=30,capture_output=True)


def exact(text):
    result = evaluate(text)
    assert result.returncode == 0, (text,result.stderr)
    record = json.loads(result.stdout)
    assert not record["approximate"], text
    return record["copy_text"]


def expected_set(value):
    return r"\{" + (str(value) if value is not None else "") + r"\}"


@lru_cache(maxsize=256)
def admissible(bound):
    return sorted({Fraction(u,v) for v in range(1,bound) for u in range(v+1) if gcd(u,v)==1})


def oracle(phase,bound):
    hits = [c for c in admissible(bound) if abs(phase-c) < Fraction(1,2*bound**2)]
    assert len(hits) <= 1
    return hits[0] if hits else None


grid = {Fraction(i,j) for j in range(2,13) for i in range(1,j)}
totals = {}
for bound in (2,3,5,7,11):
    radius = Fraction(1,2*bound**2)
    # Check either side of the strict error bound for interior and endpoint fractions.
    phases = grid | {f + k*radius/2 for f in admissible(bound) for k in (-3,-2,-1,0,1,2,3)
                     if 0 < f + k*radius/2 < 1}
    for phase in sorted(phases):
        reference = expected_set(oracle(phase,bound))
        assert exact(f"recoverphase({phase},{bound}) = {reference}") == "1", (phase,bound,reference)
    totals[str(bound)] = len(phases)

suite = json.loads((args.gui/"result.json").read_bytes())
records = json.loads((args.gui/"records.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
forms = {}
for (key, expression, mode), row in zip(inputs,records):
    assert row["id"]==key and row["label"]==row["reentry_label"]=="EXACT RESULT" and row["restored_same"]
    session = json.loads((args.gui/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert session["Expression"]==expression and session["Mode"]==int(mode)
    forms[key] = {k:row[k] for k in ("display","copy","second_copy")}
for label,phase,bound,wanted in examples:
    for form in forms["fraction-"+label].values():
        assert exact(f"({form}) = {expected_set(wanted)}") == "1", (label,form)
    for form in forms["fraction-unbound"].values():
        bound_form = f"replace((replace(({form}),α,({phase}))),N,{bound})"
        assert exact(f"({bound_form}) = {expected_set(wanted)}") == "1", (label,form)

# Independently bracket the irrational examples by rationals. Every possible
# phase in the interval has the same answer to the source's strict inequality.
brackets = [(Fraction(707106,10**6), Fraction(707107,10**6), 8, Fraction(5,7)),
            (Fraction(333,106*4), Fraction(355,113*4), 15, Fraction(11,14)),
            (Fraction(414213,10**6), Fraction(414214,10**6), 18, None)]
for lo,hi,bound,wanted in brackets:
    radius = Fraction(1,2*bound**2)
    for c in admissible(bound):
        if c==wanted:
            assert max(abs(c-lo),abs(c-hi)) < radius
        else:
            assert c+radius <= lo or c-radius >= hi

source_cases = {}
def verify(n,bindings,expected):
    for text in forms[source[n]["id"]].values():
        for name,value in bindings:
            text=f"replace(({text}),{name},({value}))"
        assert exact(text)==str(int(expected)), (n,bindings,text)
    source_cases.setdefault(str(n),[]).append(dict(bindings=bindings,expected=int(expected)))

for form in forms[source[218]["id"]].values():
    assert exact(f"({form}) = 3/16")=="1"
for n in (1,2,7):
    verify(277,[("N",n)],n>=2)
for phase in ("0","1/2","1","-1/4"):
    verify(278,[("α",phase)],0 < Fraction(phase) < 1)
for u,v in [(0,1),(1,6),(2,6),(1,0),(7,1),(-1,2)]:
    verify(279,[("u",u),("v",v),("N",7)],0<=u<7 and 0<=v<7)
    verify(280,[("v",v)],v!=0)
    verify(281,[("u",u),("v",v)],gcd(u,v)==1)
for phase in ("1/6","171/1024","3/16","49/294"):
    verify(282,[("α",phase),("u",1),("v",6),("N",21)],abs(Fraction(phase)-Fraction(1,6))<Fraction(1,882))
for offset in (-1,0,1):
    phase = Fraction(1,3)+Fraction(1,98)+Fraction(offset,9800)
    verify(282,[("α",str(phase)),("u",1),("v",3),("N",7)],offset<0)
for bad in ("0,7","1,7","-1/3,7","i,7","1/2,1","1/2,5/2"):
    assert evaluate(f"recoverphase({bad})").returncode==2

large = 2**90+7
assert exact(f"recoverphase(1/{large},{large+1}) = {expected_set(Fraction(1,large))}")=="1"
report = dict(source=inventory["source"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              exhaustive_phase_counts=totals, examples=examples, windows=forms, source_cases=source_cases,
              large_recovered_denominator=str(large))
args.report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())

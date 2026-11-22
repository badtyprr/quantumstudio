"""Check alphabet product membership against explicit ordered pairs and triples."""
import argparse
import hashlib
from itertools import product
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
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))

def evaluate(expr):
    r = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(), capture_output=True,
                       timeout=30, check=True, env=env)
    return json.loads(r.stdout)["copy_text"]

def bind(expr, pairs):
    for key, value in pairs:
        name = "n" if key == "n" else f'"{key}"'
        expr = f"replace(({expr}),{name},{value})"
    return expr

def alphabet(entries):
    return "qset(vector("+",".join(map(str, entries))+"))"

def tuple_set(axes):
    return alphabet("qtuple(vector("+",".join(map(str, t))+"))" for t in product(*axes))

cases = {}
def check(key, expr, expected):
    assert evaluate(expr) == expected, key
    cases[key] = expr, expected

sources = {}
hashes = {}
for lesson, ids in [("041", (18,20,40)), ("042", (88,90,110))]:
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    hashes[lesson] = inventory["source_sha256"]
    for number in ids:
        row = inventory["rows"][number-1]
        expr = row["literal"]
        sources[lesson,number] = expr
        copied = evaluate(expr)
        assert evaluate(copied) == copied
        cases[row["id"]] = expr, copied

definition = sources["041",18]
check("definition",definition,"1")
swapped = definition.replace("(a,b)", "(b,a)")
domain_bindings = [("Σ", alphabet((0,1))), ("Γ", alphabet((4,5,6)))]
check("swapped-coordinates",bind(evaluate(swapped),domain_bindings),"0")
for lesson, number in [("041",20),("042",110)]:
    member = evaluate(sources[lesson,number])
    for a,b in [(0,4),(1,6),(4,0),(2,5),(1,7)]:
        truth = a in (0,1) and b in (4,5,6)
        check(f"pair-{lesson}-{a}-{b}", bind(member,domain_bindings+[("a",a),("b",b)]),str(int(truth)))

series = evaluate(sources["042",88])
for axes in [((7,),), ((0,2),(1,3)), ((2,3),(4,),(6,7)), ((1,),(),(3,))]:
    sets = [(f"Σ_{i}",alphabet(items)) for i,items in enumerate(axes)]
    for early in (True,False):
        size = [("n",len(axes))]
        pairs = sets+size if early else size+sets
        check(f"series-{len(cases)}",bind(series,pairs),tuple_set(reversed(axes)))

axes = ((1,2),(4,),(8,9))
sets = [(f"Σ_{i}",alphabet(items)) for i,items in enumerate(axes)]
for lesson,number in [("041",40),("042",90)]:
    expr = evaluate(sources[lesson,number])
    for values in [(1,4,8),(2,4,9),(1,3,8),(8,4,1)]:
        coordinates = [(f"a_{i}",v) for i,v in enumerate(values)]
        expected = all(v in axis for v,axis in zip(values,axes))
        check(f"triple-{lesson}-"+"-".join(map(str,values)),bind(expr,sets+coordinates+[("n",3)]),str(int(expected)))

clipboard_checks(worker,args.windows,args.report,cases,34,dict(source_sha256=hashes, original_occurrences=6,
                 application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()))

"""Verify that the four Hadamard identities on IBM-038 remain separate."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--windows",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled.")
if args.report and not args.windows: parser.error("--report requires --windows")
worker=args.worker.resolve()
cases={}
row = json.loads(Path(__file__).with_name("ibm038-inventory.json").read_bytes())["rows"][122]
assert row["id"].endswith("M123")
source = row["literal"]
assert source.count("H ") == 4

def evaluate(expr):
    response = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                              env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")),
                              capture_output=True, timeout=30, check=True)
    value = json.loads(response.stdout)
    assert not value["approximate"]
    return value["copy_text"]

for changed in [None, 0, 1, 2, 3]:
    gates = ["H "] * 4
    expected = ["1"] * 4
    if changed is not None:
        gates[changed] = "Z "
        expected[changed] = "0"
    parts = source.split("H ")
    expression = parts[0] + "".join(gate + tail for gate,tail in zip(gates,parts[1:]))
    copied = evaluate(expression)
    assert copied == r"\begin{gathered}" + r"\\".join(expected) + r"\end{gathered}", changed
    assert evaluate(copied) == copied, changed
    cases["M123" if changed is None else f"M123-changed-{changed}"]=(expression,copied)
print("Verified all four Hadamard identities and four position-specific negative controls through Copy")

digits = json.loads(Path(__file__).with_name("ibm038-inventory.json").read_bytes())["rows"][47]
assert digits["id"].endswith("M048")
copied = evaluate(digits["literal"])
assert copied == "vector(" + ",".join(map(str, range(10))) + ")"
assert evaluate(copied) == copied
cases["M048"]=(digits["literal"],copied)
wide=digits["literal"].replace("9$","1023$")
wide_copy="vector("+",".join(map(str,range(1024)))+")"
assert evaluate(wide)==wide_copy and evaluate(wide_copy)==wide_copy
cases["range-1024"]=(wide,wide_copy)
overflow=subprocess.run([worker,"--json"],input=("quantum:"+wide.replace("1023","1024")).encode(),
                        env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")),capture_output=True,timeout=30)
assert overflow.returncode==2 and overflow.stderr.strip()
print("Verified the ten decimal digits in source order through Copy")

rows = json.loads(Path(__file__).with_name("ibm038-inventory.json").read_bytes())["rows"]
matrix_source = rows[149]["literal"].split("=",1)[1].strip("$ \n")
action_source = rows[154]["literal"]
assert rows[149]["id"].endswith("M150") and rows[154]["id"].endswith("M155")
# The previous display supplies the map. Supply the lesson's dimension
# explicitly because a single nonbinary ket does not determine its dimension.
action = action_source.replace(r"\rangle", r"\rangle_{3}").replace("A ", matrix_source + " ")
assert evaluate(action) == "1"
cases["M155-with-matrix-and-dimension"]=(action,"1")
for ket, changed in [(1,0), (2,1), (0,2)]:
    target = rf"= \vert {ket}\rangle"
    assert action.count(target) == 1
    altered=action.replace(target, rf"= \vert {changed}\rangle")
    assert evaluate(altered)=="0"
    cases[f"M155-wrong-target-{ket}"]=(altered,"0")
fourier = rows[158]["literal"]
assert rows[158]["id"].endswith("M159")
assert evaluate(fourier.replace("U =", r"\mathrm{QFT}_{4} =")) == "1"
assert evaluate(fourier.replace("U =", r"\mathrm{QFT}_{4} =").replace("& i &", "& -i &", 1)) == "0"
print("Verified the three cyclic transitions with the lesson matrix, and its separate four-dimensional Fourier example")

# Materialize the finite sum before assigning individual coefficient names.
# Each subsequent step uses the previous calculation's Copy representation.
for number in [3,4]:
    equation = evaluate(rows[number-1]["literal"])
    cases[f"M{number:03}"]=(rows[number-1]["literal"],equation)
    for vector,truth in [("[3*i;4]","1"),("[4*i;4]","0")]:
        result = equation
        for key,value in [("n","2"),("v",vector),('"α_1"',"3*i"),('"α_2"',"4")]:
            result = evaluate(f"replace(({result}),{key},{value})")
        assert result == truth, (number,vector,result)
one_based = "qonebasedcolumn(\"a_\",3,1)"
assert evaluate(one_based) == 'matrix(3,1,["a_1","a_2","a_3"])'
print("Verified one-based column dimensions, complex coefficients, norm and changed-vector controls")
if args.windows:
    clipboard_checks(worker,args.windows,args.report,cases,13,dict(source_spans=[3,4,48,123,155],
                     maximum_digit_list=1024,oversize_diagnostic=1025))

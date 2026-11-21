"""Replay the classical gate functions and both circuit wire-order conventions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--figures", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
rows = json.loads(Path(__file__).with_name("ibm045-inventory.json").read_bytes())["rows"]


def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         capture_output=True, check=True, timeout=30, env=env)
    result = json.loads(run.stdout)
    assert not result["approximate"]
    return result["copy_text"]


def literal(number):
    return rows[number - 1]["literal"]


def verify_gate(graph, outputs):
    width = 1 if len(outputs) == 2 else 2
    for index, bit in enumerate(outputs):
        assert evaluate(f"qgraphapply({graph},qbitlabel({index},{width}))") == bit


for number, outputs in [(3, "0001"), (4, "0111"), (5, "10"), (9, "0110"), (10, "0110"), (32, "0110")]:
    verify_gate(evaluate(literal(number)), outputs)
tables = evaluate(literal(6))
expected_tables = [evaluate(literal(number)) for number in (5, 3, 4)]
assert tables == "vector(" + ",".join(expected_tables) + ")"
verify_gate(evaluate(literal(10).replace("11 & 0", "11 & 1")), "0111")

for width in (1, 3):
    labels = [f'"q_{index}"' for index in range(width)]
    for number, ordered in [(37, list(reversed(labels))), (40, labels)]:
        expression = evaluate(literal(number))
        assert evaluate(f"replace(({expression}),n,{width})") == evaluate("qtuple(vector(" + ",".join(ordered) + "))")
    assert evaluate(f"replace(({evaluate(literal(39))}),n,{width})") == labels[-1]
assert evaluate(literal(38)) == '"q_0"'
print("Verified all gate inputs, the three side-by-side truth tables, a changed output, and both wire orders.")

if args.figures is None:
    if args.report: parser.error("--report requires --figures")
    raise SystemExit
if not args.report: parser.error("--figures requires --report")
inventory = json.loads(Path(__file__).with_name("ibm045-inventory.json").read_bytes())
sources = {}
for figure in inventory["figures"]:
    name = Path(figure["path"]).name
    sources[name] = dict(source=inventory["source"].split("/learning/courses/")[0] + "/public" + figure["path"],
                         sha256=hashlib.sha256((args.figures / name).read_bytes()).hexdigest(), checks=[])


def check(names, expression, expected):
    actual = evaluate(expression)
    assert actual == evaluate(expected), (expression, expected, actual)
    for name in names.split():
        sources[name + ".svg"]["checks"].append(dict(expression=expression, expected=expected))


# The source orders wires bottom-to-top, so the top control is the rightmost bit.
top_control = "(SWAP*CNOT*SWAP)"
for y in (0, 1):
    for x in (0, 1):
        names = "Boolean-circuit-XOR Boolean-circuit-classic"
        if (y, x) == (1, 0): names += " XOR-circuit-evaluate"
        check(names, f"({y} and not {x}) or ((not {y}) and {x})", str(x ^ y))
        check("cNOT controlled-gates", f"{top_control}*|{x}{y}>", f"|{x^y}{y}>")
        check("swap-gate", f"SWAP*|{y}{x}>", f"|{x}{y}>")
check("arithmetic-circuit", "(x*x+y)*(y+1)==x^2*y+x^2+y^2+y", "1")
chain = "T*H*S*H"
check("simple-quantum-circuit simple-quantum-circuit-evaluated", f"{chain}*|0>==[(1+i)/2;1/sqrt(2)]", "1")
check("ebit-circuit-first", "(I@H)*|00>", "[1;1;0;0]/sqrt(2)")
bell = f"{top_control}*(I@H)*|00>"
check("ebit-circuit ebit-circuit-second", bell, "[1;0;0;1]/sqrt(2)")
check("ebit-circuit-measured ebit-circuit-measured-compact", f"probs({bell})", "[1/2;0;0;1/2]")
for gate, output in [("X","|1>"), ("Y","i*|1>"), ("Z","|0>"), ("H","|+>"), ("S","|0>"), ("T","|0>")]:
    check("single-qubit-gates", gate + "*|0>", output)
for gate, output in [("X","|0>"), ("Y","-i*|0>"), ("Z","-|1>"), ("H","|->"), ("S","i*|1>"), ("T","(1+i)/sqrt(2)*|1>")]:
    check("single-qubit-gates", gate + "*|1>==" + output, "1")
check("not-gate", "X*|0>", "|1>")
check("not-gate", "X*|1>", "|0>")
reverse = "((SWAP@I)*(I@SWAP)*(SWAP@I))"
for index in range(8):
    a, b, c = map(int, f"{index:03b}")
    check("controlled-gates", f"{reverse}*Toffoli*{reverse}*|{c}{b}{a}>", f"|{c^(a&b)}{b}{a}>")
    swapped = f"{b}{c}" if a else f"{c}{b}"
    check("controlled-gates", f"{reverse}*CSWAP*{reverse}*|{c}{b}{a}>", f"|{swapped}{a}>")
    check("uncontrolled-and-controlled-unitary", f"{reverse}*qcontrolled(SWAP)*{reverse}*|{c}{b}{a}>", f"|{swapped}{a}>")
assert len(sources) == 17 and all(source["checks"] for source in sources.values())
report = dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), figures=sources)
args.report.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print("Verified the operations and measurement distributions represented by all 17 circuit diagrams.")

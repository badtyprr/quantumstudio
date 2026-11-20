"""Replay the twelve IBM-028 circuit and geometry figures against the packaged worker."""
import argparse
import cmath
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("figures", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
plots = {4, 6, 10, 16, 17}
pinned = {
    1: "6b1b0e577c2e2a71aaa0d94f9cceaa089d9ea9159ee31d5e47a537c69c1abec6",
    2: "504cdb3eebcc106ec5a8f8c742d5aceb2c53f6b740a55e896fd5d7a14910d5be",
    3: "5fa7c37960ed2ed1c3754ff20d02faebc4b39131bb3ce0a2840a77c3db8633d6",
    5: "a79aa78b6b1ca06e80e9b1263fcf4b129b0f6f0a87736fe432f9e586d9adaa71",
    7: "bca642db5f5e1840831657534f406d38e35feb6f281b01ae5715dcba6d63f021",
    8: "bfbdc88ba76f7bbd83d5fbe0a178d2a1e6ac091b41c9467b5cdae4faec31e696",
    9: "0e2a9c1aae8e02e4cc47f3b96ad9a9fde77e351454186e62a65c3e6942a9b4ef",
    11: "5bb78afe9f40baf115cd3a976d42b8dce977450e8c51b8657f5ea196014753a7",
    12: "2bc6ce75baeb27fbc15f9de9de625c2a1b2b7a50c2c35d57b4751a1e6ee0c3a8",
    13: "42f01e56839b4bbd1bd70780d6f40d2e784bac201af908ffafd4f38762a7edbf",
    14: "e020bab4e585bbaf1668d2195de555013bb1209a3288b83bcabcdf1446521dc0",
    15: "5ba09f7537e134d06f1194af83c80b345c0b0100a051e8157996a72583989677",
}
report = {}


def run(expr, approximate=False):
    command = [worker, "--json"]
    if approximate:
        command.append("--approx")
    p = subprocess.run(command, input=("quantum:" + expr).encode(), timeout=60, capture_output=True)
    assert p.returncode == 0, (expr, p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]


def sequence(ops, initial):
    if not ops:
        return initial
    steps = [f"apply({gate},s_0,[{','.join(map(str, wires))}])" for gate, wires in ops]
    return f"sequence([{','.join(steps)}],{initial},s_0)"


def state(figure, name, actual, expected, unequal=False):
    text = run(f"norm(({actual})-({expected}))", True)
    error = abs(complex(text.replace(" ", "").replace("−", "-").replace("i", "j")))
    assert math.isfinite(error) and (error > 0.1 if unequal else error < 1e-12), (figure, name, error)
    report[figure]["checks"].append(dict(case=name, actual=actual, expected=expected,
                                         unequal=unequal, norm_difference=error))


def basis(k, n):
    return f"basis({k},{n})"


def upper_column(amplitudes):
    n = len(amplitudes)
    return f"matrix({2*n},1,[{','.join(['0'] * n + amplitudes)}])"


for number, figure in enumerate(inventory["figures"], 1):
    if number in plots:
        continue
    name = Path(figure["path"]).name
    raw = (args.figures / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pinned[number], name
    root = ET.fromstring(raw)
    assert root.tag.endswith("}svg")
    report[number] = dict(id=f"IBM028-F{number:02}", file=name, alt=figure["alt"],
                          sha256=hashlib.sha256(raw).hexdigest(), checks=[])

# Source order is little-endian from top to bottom. The worker numbers wires
# from the left of the ket, so the target register is its most significant bit.
for target in range(2):
    phase = "i" if target == 0 else "(-i)"
    state(1, f"Y on {target}", f"Y*{basis(target,2)}", f"{phase}*{basis(1-target,2)}")
    for control in range(2):
        k = 2*target + control
        expected = f"{phase}*{basis(2*(1-target)+1,4)}" if control else basis(k,4)
        state(1, f"control {control}, target {target}", sequence([("controlled(Y)", [1,0])], basis(k,4)), expected)

initial = basis(2,4)
h = ("H", [1])
kick = ("controlled(S)", [1,0])
single = [h, kick, h]
stages = [initial, upper_column(["1/sqrt(2)", "1/sqrt(2)"]),
          upper_column(["1/sqrt(2)", "i/sqrt(2)"]), upper_column(["(1+i)/2", "(1-i)/2"])]
for k, expected in enumerate(stages):
    state(3, f"pi_{k}", sequence(single[:k], initial), expected)
state(2, "quarter turn", sequence(single, initial), stages[-1])
state(5, "quarter turn doubled", sequence([h, kick, kick, h], initial), basis(3,4))
state(5, "single kick differs", sequence(single, initial), basis(3,4), unequal=True)

for y in range(4):
    phase_gate = f"controlled(P(2*pi*{y}/4))"
    setup = [("H", [1]), ("H", [2])]
    low = (phase_gate, [2,0])
    high = (phase_gate, [1,0])
    preparation = setup + [low, high, high]
    for k, (gates, powers) in enumerate([(setup, [0]*4), (setup+[low], [0,1,0,1]),
                                         (preparation, list(range(4)))], 1):
        expected = upper_column([f"exp(2*pi*i*{power*y}/4)/2" for power in powers])
        state(8, f"pi_{k}, phase {y}/4", sequence(gates,basis(4,8)), expected)
    state(7, f"phase {y}/4", sequence(preparation,basis(4,8)), expected)
    state(9, f"estimate {y}", sequence(preparation+[("qfourier(4)~", [1,2])],basis(4,8)), basis(4+y,8))

for k in range(4):
    expected = f"exp(i*pi/4)*{basis(k,4)}" if k == 3 else basis(k,4)
    for gate, wires in [("controlled(P(pi/4))", [0,1]), ("controlled(P(pi/4))", [1,0]), ("CP(pi/4)", [0,1])]:
        state(11, f"{gate} on {wires}, input {k}", sequence([(gate,wires)],basis(k,4)), expected)

injection = [(f"CP(pi/{16>>j})", [4,3-j]) for j in range(4)]
rotate = [("SWAP", [4,0]), ("SWAP", [4,3]), ("SWAP", [3,2]), ("SWAP", [2,1])]
decomposition = [("qfourier(16)", [0,1,2,3])] + injection + [("H",[4])] + rotate
for k in range(32):
    y, a = divmod(k, 2)
    state(12, f"a={a}, y={y}", sequence(injection,basis(k,32)), f"exp(2*pi*i*{a*y}/32)*{basis(k,32)}")
    state(13, f"Fourier column {k}", sequence(decomposition,basis(k,32)), f"qfourier(32)*{basis(k,32)}")
state(13, "output permutation matters", sequence(decomposition[:-1],basis(1,32)), f"qfourier(32)*{basis(1,32)}", unequal=True)

for m in (1, 2, 3, 4):
    n = 2**m
    for y in range(n):
        gates = [("H", [m-j]) for j in range(m)]
        gates += [(f"controlled(P(2*pi*{(2**j)*y}/{n}))", [m-j,0]) for j in range(m)]
        gates.append((f"qfourier({n})~", list(range(1,m+1))))
        state(14, f"{m} bits, phase {y}/{n}", sequence(gates,basis(n,2*n)), basis(n+y,2*n))

# Check a non-grid phase with a target eigenstate in superposition. The
# Fourier sum predicts the entire output vector, including relative phases.
n = 8
theta = Fraction(3, 16)
gates = [("H", [j]) for j in (1, 2, 3)]
for j in range(3):
    angle = 2 * theta * 2**j
    gates.append((f"controlled(H*P(pi*({angle}))*H)", [3-j,0]))
gates.append(("qfourier(8)~", [1,2,3]))
amplitudes = []
for y in range(n):
    amplitude = sum(cmath.exp(2j*math.pi*x*(theta-y/n)) for x in range(n)) / n
    amplitudes.append(f"({amplitude.real:.17g}+({amplitude.imag:.17g})*i)")
expected = "|-> @ matrix(8,1,[" + ",".join(amplitudes) + "])"
state(14, "off-grid phase 3/16, target |->", sequence(gates, "|-> @ basis(0,8)"), expected)

# Compare the plotted blue chord and purple arc in their shared SVG frame.
geometry = ET.parse(args.figures / report[15]["file"])
paths = {p.get("id"): p for p in geometry.iter() if p.tag.endswith("}path")}
chord_path, arc_path = paths["path9"], paths["path17"]
assert chord_path.get("transform") == arc_path.get("transform")
def point(pair):
    x, y = map(float, pair.split(","))
    return complex(x, y)

move, start, stop = chord_path.get("d").split()
assert move == "M"
start, stop = point(start), point(stop)
move, origin, cubic, *pairs = arc_path.get("d").split()
assert move == "m" and cubic == "c" and point(origin) == start and len(pairs) % 3 == 0
a = start
length = 0
for k in range(0, len(pairs), 3):
    b, c, end = [a + point(pair) for pair in pairs[k:k+3]]
    prev = a
    for j in range(1, 257):
        t = j / 256
        current = (1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*end
        length += abs(current-prev)
        prev = current
    a = end
assert abs(a-stop) < 1e-5 and abs(abs(stop)/abs(start)-1) < 1e-5
drawn_phase = cmath.phase(stop/start)/(2*math.pi)
drawn_chord, drawn_arc = abs(stop-start)/abs(start), length/abs(start)
assert abs(drawn_chord-2*abs(math.sin(math.pi*drawn_phase))) < 1e-5
assert abs(drawn_arc-2*math.pi*abs(drawn_phase)) < 0.001
report[15]["drawing"] = dict(phase=drawn_phase, chord=drawn_chord, arc=drawn_arc)

for delta in [Fraction(i,32) for i in range(-16,17)]:
    chord = float(run(f"abs(exp(2*pi*i*({delta}))-1)", True))
    arc = float(run(f"2*pi*abs({delta})", True))
    assert abs(chord-2*abs(math.sin(math.pi*delta))) < 1e-12
    assert abs(arc-2*math.pi*abs(delta)) < 1e-12
    assert 4*abs(delta)-1e-12 <= chord <= arc+1e-12
    report[15]["checks"].append(dict(delta=str(delta), chord=chord, arc=arc))

assert all(entry["checks"] for entry in report.values()) and len(report) == 12
result = dict(notebook=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              tolerance=1e-12, figures=list(report.values()))
# M191 writes the final row terminator with presentation spacing. The
# complete source matrix equals QFT8. Changing one coefficient must fail.
matrix = next(r["literal"] for r in inventory["rows"] if r["id"].endswith("M191"))
changed = matrix.replace("1 & 1 & 1", "-1 & 1 & 1", 1)
assert changed != matrix and run(matrix) == "1" and run(changed) == "0"
result["M191"] = dict(source_result="1", changed_first_entry_result="0")
args.output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+"\n").encode())
print({k: len(v["checks"]) for k,v in report.items()})

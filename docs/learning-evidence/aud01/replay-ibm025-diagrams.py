"""Replay the eight IBM-025 figures using exact amplitudes and the printed wire order."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("diagrams", type=Path, help="Directory containing the eight pinned SVGs")
parser.add_argument("--gui-inputs", type=Path, help="Write the same circuit checks for the Windows GUI replay")
args = parser.parse_args()
worker = args.worker.resolve()
manifest = json.loads(Path(__file__).with_name("ibm025-diagrams.json").read_bytes())
for figure in manifest:
    assert hashlib.sha256((args.diagrams / figure["file"]).read_bytes()).hexdigest() == figure["sha256"]

counts = {}
gui_inputs = []

def verify(figure, wires, operations, start, expected, truth=True):
    # The figure numbers its top wire as the least significant bit. The
    # calculator's apply() numbers wire zero from the left of the ket.
    steps = []
    for gate, *targets in operations:
        mapped = ",".join(str(wires - 1 - wire) for wire in targets)
        steps.append(f"apply({gate},s_0,[{mapped}])")
    expr = f"sequence([{','.join(steps)}],basis({start},{2**wires}),s_0)=basis({expected},{2**wires})"
    proc = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                          capture_output=True, timeout=60, check=True)
    result = json.loads(proc.stdout)
    assert not result["approximate"] and result["copy_text"] == str(int(truth)), (figure, start, result["text"])
    counts[figure] = counts.get(figure, 0) + 1
    gui_inputs.append([f"{Path(figure).stem}-{counts[figure]:02d}-{int(truth)}", expr])

def cx(a, b):
    return ("CNOT", a, b)

def swap(a, b):
    return [cx(a, b), cx(b, a), cx(a, b)]

toffoli = [("Toffoli", 0, 1, 2)]
decomposition = [("H", 2), cx(1, 2), ("T~", 2), cx(0, 2), ("T", 2), cx(1, 2),
                 ("T~", 2), cx(0, 2), ("T", 1), ("T", 2), cx(0, 1),
                 ("T", 0), ("T~", 1), ("H", 2), cx(0, 1)]
for state in range(8):
    target = state ^ (4 if state & 3 == 3 else 0)
    verify("Toffoli-gate.svg", 3, toffoli, state, target)
    verify("build-Toffoli.svg", 3, decomposition, state, target)

boolean = "AND-OR-FANOUT-with-Toffoli.svg"
for x in range(4):
    verify(boolean, 3, toffoli, x, x | (4 if x == 3 else 0))
    # The printed OR circuit leaves the two source wires complemented.
    verify(boolean, 3, [("X", 0), ("X", 1)] + toffoli + [("X", 2)],
           x, (x ^ 3) | (4 if x else 0))
    verify("swap.svg", 2, swap(0, 1), x, ((x & 1) << 1) | (x >> 1))
for x in range(2):
    verify(boolean, 2, [cx(0, 1)], x, x * 3)

# The next three drawings leave R abstract. Instantiate f(a,b)=a AND b.
# R puts f on wire zero and saves (b,a) on the two garbage wires.
compute = toffoli + swap(0, 2)
query = compute + [cx(0, 3)] + compute[::-1]
for x in range(4):
    f = int(x == 3)
    garbage = ((x >> 1) & 1) | ((x & 1) << 1)
    verify("reversible-circuit-simulation.svg", 3, compute, x, f | (garbage << 1))
    for y in range(2):
        start = x | (y << 3)
        finish = x | ((y ^ f) << 3)
        verify("garbage-free-computation.svg", 4, query, start, finish)
        verify("simulation-as-query-gate.svg", 4, query, start, finish)

# Instantiate the last figure with a non-self-inverse two-bit permutation.
# The scratch bit at wire two holds the complemented low bit temporarily.
def increment_query(inverse):
    return [cx(0, 2), ("X", 2), cx(2, 3), cx(1, 4),
            cx(2 if inverse else 0, 4), ("X", 2), cx(0, 2)]
exchange = swap(0, 3) + swap(1, 4)
for x in range(4):
    goal = (x + 1) % 4
    for inverse in (True, False):
        verify("fully-reversible-simulation.svg", 5, increment_query(False) + exchange + increment_query(inverse),
               x, goal, truth=inverse)
assert set(counts) == {entry["file"] for entry in manifest}
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(gui_inputs), encoding="utf-8")
print(json.dumps(counts, indent=2))

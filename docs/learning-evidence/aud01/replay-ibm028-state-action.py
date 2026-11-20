"""Compare the lesson's state mapping to its independently assembled controlled phases."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
row = inventory["rows"][223]
assert row["id"].endswith("M224")


def evaluate(text):
    result = subprocess.run([worker, "--json"], input=("quantum:" + text).encode(),
                            env=env, capture_output=True, timeout=60)
    assert result.returncode == 0, (text[:150], result.stderr.decode())
    return json.loads(result.stdout)


def copied(text):
    return evaluate(text)["copy_text"]


def circuit(width, omit_high=False):
    # The last bit is a. Each CP acts on a and one bit of y. All are diagonal,
    # so multiplying their diagonal entries composes them without reordering wires.
    size = 2 ** width
    factors = []
    for bit in range(width - 1 - int(omit_high)):
        gate = f"CP(2*pi*{2**bit}/{size})"
        factors.append([copied(f"element({gate},{index},{index})") for index in range(1, 5)])
    diagonal = []
    for word in range(size):
        phase = [entries[2*((word >> (bit+1)) & 1) + (word & 1)] for bit, entries in enumerate(factors)]
        diagonal.append(copied("*".join(f"({x})" for x in phase if x != "1") or "1"))
    values = [diagonal[r] if r == c else "0" for r in range(size) for c in range(size)]
    return f"matrix({size},{size},[" + ",".join(values) + "])"


record = evaluate(row["literal"])
assert copied(record["copy_text"]) == record["copy_text"]
forms = [record["display_text"], record["copy_text"]]
gui = [[row["id"], row["literal"], "0"]]
results = []
for width in (2, 3, 4, 5):
    size = 2 ** width
    gate, missing = circuit(width), circuit(width, omit_high=True)
    for y in range(size//2):
        for a in (0, 1):
            affected = bool(a and y & (size//4))
            for form in forms:
                bound = form
                for label, value in [("|y>", f"basis({y},{size//2})"), ("|a>", f"basis({a},2)"),
                                     ("m", width), ("y", y), ("a", a),
                                     (f"ω_{size}", f"exp(2*pi*i/{size})")]:
                    bound = f"replace(({bound}),{label},({value}))"
                for name, operator, expected in [("all", gate, "1"), ("missing", missing, str(int(not affected)))]:
                    expression = f"checkaction({operator},({bound}))"
                    actual = copied(expression)
                    assert actual == expected, (width, y, a, name, actual)
                    if width == 2 and y == 1 and form == forms[0]:
                        gui.append([f"M224-a{a}-{name}-{expected}", expression, "0"])
            results.append(dict(width=width, y=y, a=a, missing_gate_changes_phase=affected))
# Explicit multiplication in copied exponents also affects these two identities.
related = {}
for number in (199, 265):
    item = inventory["rows"][number-1]
    relation = evaluate(item["literal"])
    comparisons = 0
    for form in (relation["display_text"], relation["copy_text"]):
        for bit in (0, 1):
            for wrong in (False, True):
                if number == 199:
                    # The RHS says whether the columns y and z are identical.
                    bindings = [("φ_z", "fourier(4)*basis(1,4)"),
                                ("φ_y", f"fourier(4)*basis({bit ^ wrong},4)"),
                                ("ω_N", "i"), ("N", 4), ("z", 1), ("y", bit)]
                else:
                    # An odd x*y detects the wrong sign for the smaller root.
                    bindings = [("m", 3), ("ω_8", "exp(pi*i/4)"), ("ω_4", "-i" if wrong else "i"),
                                ("x", 1), ("y", 3), ("a", 1), ("b", bit)]
                test = form
                for label, value in bindings:
                    test = f"replace(({test}),{label},({value}))"
                assert copied(test) == str(int(not wrong)), (number, bit, wrong)
                comparisons += 1
    related[item["id"]] = comparisons

report = dict(source=inventory["source"], id=row["id"], literal=row["literal"],
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              display=record["display_text"], copy=record["copy_text"], cases=results, related_comparisons=related)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())

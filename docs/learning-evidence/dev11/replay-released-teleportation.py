"""Recheck the published IBM-066 circuit adaptations using the extracted Windows release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile

if not __debug__:
    raise RuntimeError("This audit requires Python assertions to be enabled.")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("application", type=Path, help="extracted QuantumStudio directory")
args = parser.parse_args()
app = args.application.resolve()
here = Path(__file__).resolve().parent
lesson = runpy.run_path(str(here / "replay-teleportation-controls.py"))
worker = app / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(app / "data"))


def evaluate(expr):
    request = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                             capture_output=True, check=True, env=env, timeout=30)
    result = json.loads(request.stdout)
    assert not result["approximate"], expr
    return result["copy_text"]


assert evaluate("$5$") == "5"
# One concrete instance of the five-wire code suggested by the illustration.
generators = ["XZZXI", "IXZZX", "XIXZZ", "ZXIXZ"]
group = "vector(" + ",".join(f"compact_pauli({g})" for g in generators) + ")"
assert evaluate(f"compact_dimension({group})") == "2"
assert evaluate(f"compact_distance({group},3)") == "3"
syndromes = set()
for wire in range(5):
    for pauli in "XYZ":
        error = "I" * wire + pauli + "I" * (4 - wire)
        bits = [int(g[wire] not in ("I", pauli)) for g in generators]
        syndrome = evaluate(f"compact_syndrome({group},compact_pauli({error}))")
        assert syndrome == "vector(" + ",".join(map(str, bits)) + ")"
        syndromes.add(tuple(bits))
assert len(syndromes) == 15 and (0, 0, 0, 0) not in syndromes

# Each location independently fails with probability 1/10 or 1/5.
# Conditional on a fault, both locations use the same fair X/Z selector.
# The row and column alphabets are (no fault, X, Z). Work in units of 1/100.
joint = [[72, 9, 9], [4, 1, 0], [4, 0, 1]]
assert sum(map(sum, joint)) == 100
first_fault = sum(map(sum, joint[1:]))
second_fault = sum(sum(row[1:]) for row in joint)
both_fault = sum(sum(row[1:]) for row in joint[1:])
assert (first_fault, second_fault, both_fault) == (10, 20, 2)
assert evaluate(f"{both_fault}/100==({first_fault}/100)*({second_fault}/100)") == "1"
assert evaluate(f"({first_fault}+{second_fault}-{both_fault})/100==7/25") == "1"
# A mixed X/Z pair has zero joint mass despite positive single-site marginals.
assert joint[1][2] == joint[2][1] == 0 and joint[1][1] == joint[2][2] == 1

records = []
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    cases = {}
    for logical in (False, True):
        for wiring in ("diagram", "teleportation-control"):
            for index, state in enumerate([*lesson["PREP"], "Bell"]):
                label = f"{int(logical)}-{wiring}-{index}"
                (root / (label + ".qasm")).write_bytes(lesson["circuit"](state, wiring, logical))
                cases[label] = lesson["expected_bits"](state, wiring)

    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    here / "replay-released-teleportation.ps1", root, app], check=True, timeout=300)
    for label, expected in cases.items():
        row = {"case": label}
        for mode, flag in (("exact", "--exact-circuit"), ("sampled", "--sample")):
            request = (root / f"{label}.{mode}").read_bytes()
            p = subprocess.run([worker, flag], input=request, capture_output=True,
                               check=True, env=env, timeout=60)
            result = json.loads(p.stdout)
            if mode == "exact":
                observed = {k: float(v) for k, v in result["probabilities"].items()}
            else:
                assert sum(result["counts"].values()) == 10000
                observed = {k: v / 10000 for k, v in result["counts"].items()}
            assert set(observed) == set(expected), label
            delta = max(abs(observed[k] - v) for k, v in expected.items())
            assert delta <= (1e-10 if mode == "exact" else .03), label
            row[mode + "_max_error"] = delta
        records.append(row)

print(json.dumps(dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                      single_wire_syndromes=len(syndromes), circuits=records), indent=2))

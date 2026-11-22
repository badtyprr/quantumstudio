"""Evaluate all IBM-063 illustrated error and recovery chains on the full torus."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("figures", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
here = Path(__file__).resolve().parent
illustrations = runpy.run_path(str(here / "replay-ibm063-lattice.py"))
baseline = json.loads((here / "ibm063-lattice.json").read_bytes())["figures"]
side = 9
period = 2 * side
edges = [(x, y) for x in range(period) for y in range(period) if (x + y) % 2]
index = {edge: i for i, edge in enumerate(edges)}
width = len(edges)


def word(points):
    value = sum(1 << index[p] for p in points)
    return f"bitstring({value},{width})"


def evaluate(expression):
    proc = subprocess.run([worker, "--json"], input="quantum:" + expression,
                          text=True, encoding="utf8", capture_output=True, env=env, timeout=30)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip())
    result = json.loads(proc.stdout)
    if result["approximate"]:
        raise ValueError("Expected exact binary results")
    return result["copy_text"]


def parities(chain, checks):
    # Each original square shares its four edge qubits with its neighbors.
    # Evaluate one lattice row at a time within the notation complexity limit.
    terms = [f"bitdot({chain},{check})" for check in checks]
    bits = []
    for start in range(0, len(terms), side):
        copy = evaluate("vector(" + ",".join(terms[start:start + side]) + ")")
        if not copy.startswith("vector(") or not copy.endswith(")"):
            raise ValueError(copy)
        bits.extend(map(int, copy[7:-1].split(",")))
    return bits


faces = {}
for x in range(1, period, 2):
    for y in range(1, period, 2):
        faces[x, y] = word({((x + dx) % period, (y + dy) % period)
                            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))})
cuts = [word({edge for edge in edges if edge[axis] == 0}) for axis in (0, 1)]
verified = {}
for name, (_, _, _, winding) in illustrations["cases"].items():
    path = args.figures / (name + ".svg")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == baseline[name]["sha256"]
    errors, recovery, shaded = illustrations["diagram"](path)
    row = {}
    for label, chain in (("error", errors), ("recovery", recovery)):
        if not chain:
            continue
        bits = parities(word(chain), faces.values())
        assert len(bits) == len(faces) and all(bit in (0, 1) for bit in bits)
        negative = [point for point, bit in zip(faces, bits) if bit]
        assert set(negative) == shaded, (name, label, negative, shaded)
        row[label + "_negative_faces"] = negative
    if winding is not None:
        residual = f"bitxor({word(errors)},{word(recovery)})"
        assert parities(residual, faces.values()) == [0] * len(faces)
        actual = parities(residual, cuts)
        assert tuple(actual) == winding, (name, actual, winding)
        row["residual_winding"] = actual
    verified[name] = row

print(json.dumps({"qubits": width, "face_checks_per_chain": len(faces),
                  "worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
                  "figures": verified}, indent=2))

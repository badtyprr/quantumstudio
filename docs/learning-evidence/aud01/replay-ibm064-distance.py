"""Check native compact distance against the illustrated codes and exhaustive small Pauli groups."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import runpy
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("figures", type=Path)
args = parser.parse_args()
if not __debug__:
    raise RuntimeError("The distance checks require Python assertions.")
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def distance(n, generators, bound, expected):
    rows = [f"[{n},{x},{z},{(-(x & z).bit_count()) % 4}]" for x, z in generators]
    expression = f"compact_distance(vector({','.join(rows)}),{bound})"
    proc = subprocess.run([worker, "--json"], input="quantum:" + expression, text=True,
                          encoding="utf8", env=env, capture_output=True, timeout=30)
    if expected is None:
        assert proc.returncode and "within the requested weight bound" in proc.stderr, proc.stderr
    else:
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)
        assert not result["approximate"] and result["copy_text"] == str(expected), expression


here = Path(__file__).resolve().parent
extract = runpy.run_path(str(here / "replay-ibm064-figures.py"))
reference = json.loads((here / "ibm064-figures.json").read_bytes())
figures = {}
for name in ("Steane-color-code", "color-code", "rotated-surface-code"):
    path = args.figures / (name + ".svg")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == reference[name]["sha256"]
    n, xs, zs = extract["stabilizer_masks"](path)
    expected = extract["analyze"](path)["distance"]
    generators = [(x, 0) for x in xs] + [(0, z) for z in zs]
    distance(n, generators, expected - 1, None)
    distance(n, generators, expected, expected)
    distance(n, generators, n, expected)
    figures[name] = {"qubits": n, "distance": expected}

# Independent enumeration, including mixed and degenerate codes. Ignore global phases.
rng = random.Random(64064)
histogram = {}
for n in range(2, 7):
    for trial in range(12):
        span = {(0, 0)}
        checks = []
        target_rank = 1 + trial % (n - 1)
        while len(checks) < target_rank:
            x, z = rng.randrange(1 << n), rng.randrange(1 << n)
            if (x, z) in span or any(((x & b) ^ (z & a)).bit_count() % 2 for a, b in checks):
                continue
            span |= {(a ^ x, b ^ z) for a, b in span}
            checks.append((x, z))
        best = min((x | z).bit_count() for x in range(1 << n) for z in range(1 << n)
                   if (x, z) not in span and all(((x & b) ^ (z & a)).bit_count() % 2 == 0
                                                  for a, b in checks))
        distance(n, checks, n, best)
        histogram[best] = histogram.get(best, 0) + 1

print(json.dumps({"worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
                  "figures": figures, "exhaustive_small_code_distances": histogram}, indent=2))

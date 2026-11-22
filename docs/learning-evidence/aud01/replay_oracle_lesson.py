"""Verify source spans, Copy round trips and concrete bindings on a calculator worker."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess


def replay_lesson(description, inventory_name, total, mode, cases):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("worker", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    inventory = json.loads(Path(__file__).with_name(inventory_name).read_bytes())
    raw = args.notebook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != inventory["source_sha256"]:
        raise ValueError("The notebook differs from the pinned lesson")
    cells = json.loads(raw)["cells"]
    worker = args.worker.resolve()
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def evaluate(expression):
        p = subprocess.run([str(worker), "--json"], input=("quantum:"+expression).encode(),
                           capture_output=True, check=True, timeout=30, env=env)
        value = json.loads(p.stdout)
        if value["approximate"]:
            raise ValueError(f"Unexpected approximation for {expression}")
        return value["copy_text"]

    copies = {}
    for i,row in enumerate(inventory["rows"], 1):
        s = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        if s != row["literal"] or row["id"].split("-")[-1] != f"M{i:03}":
            raise ValueError(f"M{i:03} source differs")
        copy = evaluate(mode(i) + s)
        if copy != evaluate(mode(i) + copy):
            raise ValueError(f"M{i:03} changed on Copy re-entry")
        copies[i] = copy
    if len(copies) != total:
        raise ValueError(f"Expected {total} source occurrences")
    checks = list(cases())

    def check(case):
        i, bindings, expected = case
        expr = copies[i]
        for key,value in bindings:
            expr = f"replace(({expr}),{key},{value})"
        actual = evaluate(expr)
        if actual != expected:
            raise ValueError(f"M{i:03} expected {expected}, got {actual}")

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(check, checks))
    print(f"Verified {len(copies)} source formulas and {len(checks)} bound results.")

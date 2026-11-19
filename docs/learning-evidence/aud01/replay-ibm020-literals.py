"""Observe IBM-020 source literals through the native worker's Quantum mode."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def evaluate(worker, env, literal):
    delimiter = "$$" if literal.startswith("$$") else "$"
    if not literal.startswith(delimiter) or not literal.endswith(delimiter):
        raise ValueError(f"Expected a delimited formula: {literal!r}")
    request = "quantum:" + literal[len(delimiter):-len(delimiter)]
    process = subprocess.run([worker, "--json"], input=request.encode(), env=env,
                             capture_output=True, timeout=30)
    record = {"input": request, "exit": process.returncode}
    if process.returncode == 0:
        record["output"] = json.loads(process.stdout)
    elif process.returncode != 2 or not process.stderr.strip():
        raise RuntimeError(f"Unexpected worker exit {process.returncode}: {process.stderr!r}")
    if process.stderr:
        record["stderr"] = process.stderr.decode().strip()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("notebook", "worker", "definitions", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    index = json.loads((HERE / "ibm020-inventory-map.json").read_bytes())
    raw = args.notebook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != index["current_sha256"]:
        raise ValueError("Notebook hash mismatch")
    cells = json.loads(raw)["cells"]
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.definitions.resolve(strict=True)))
    records = []
    for cell in index["cells"]:
        source = "".join(cells[cell["index"]]["source"])
        for identifier, start, end in cell.get("formulas", []):
            result = evaluate(args.worker, env, source[start:end])
            records.append({"id": identifier, "cell": cell["index"], **result})
    if len({row["id"] for row in records}) != 168 or len(records) != 168:
        raise ValueError("Incomplete literal inventory")
    controls = []
    for row in records:
        body = row["input"].removeprefix("quantum:").rstrip()
        if row.get("stderr", "").startswith("Unexpected notation") and body.endswith((",", ".")):
            adjusted = evaluate(args.worker, env, "$" + body[:-1] + "$")
            controls.append({"parent": row["id"], "removed": body[-1], **adjusted})
    report = {"trailing_punctuation_controls": controls,"source_sha256": index["current_sha256"],
              "worker_sha256": hashlib.sha256(args.worker.read_bytes()).hexdigest(),
              "mode": "Quantum, no authored bindings; only outer math delimiters removed",
              "scope": "Exit zero records returned output. Correctness requires checking each expression in its lesson context.",
              "exit_counts": dict(Counter(row["exit"] for row in records)),
              "records": records}
    args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

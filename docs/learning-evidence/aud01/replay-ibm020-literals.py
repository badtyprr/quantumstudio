"""Observe IBM-020 source literals through the native worker's Quantum mode."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def evaluate(worker, env, literal, keep_delimiters=False):
    delimiter = "$$" if literal.startswith("$$") else "$"
    if not literal.startswith(delimiter) or not literal.endswith(delimiter):
        raise ValueError(f"Expected a delimited formula: {literal!r}")
    request = "quantum:" + (literal if keep_delimiters else literal[len(delimiter):-len(delimiter)])
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
    parser.add_argument("--compare-wrapped", type=Path, metavar="CANDIDATE",
                        help="Compare baseline and candidate using the full original literals")
    args = parser.parse_args()
    index = json.loads((HERE / "ibm020-inventory-map.json").read_bytes())
    raw = args.notebook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != index["current_sha256"]:
        raise ValueError("Notebook hash mismatch")
    cells = json.loads(raw)["cells"]
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.definitions.resolve(strict=True)))
    records = []
    differences = []
    candidate_counts = Counter()
    for cell in index["cells"]:
        source = "".join(cells[cell["index"]]["source"])
        for identifier, start, end in cell.get("formulas", []):
            literal = source[start:end]
            result = evaluate(args.worker, env, literal, bool(args.compare_wrapped))
            if args.compare_wrapped:
                candidate = evaluate(args.compare_wrapped, env, literal, True)
                candidate_counts[candidate["exit"]] += 1
                if result != candidate:
                    differences.append({"id": identifier, "baseline": result, "candidate": candidate})
            records.append({"id": identifier, "cell": cell["index"], **result})
    if len({row["id"] for row in records}) != 168 or len(records) != 168:
        raise ValueError("Incomplete literal inventory")
    worker_hash = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    exit_counts = dict(Counter(row["exit"] for row in records))
    if args.compare_wrapped:
        report = {"source_sha256": index["current_sha256"],
                  "baseline_worker": worker_hash,
                  "candidate_worker": hashlib.sha256(args.compare_wrapped.read_bytes()).hexdigest(),
                  "mode": "Quantum, original source delimiters, no authored bindings",
                  "baseline_exit_counts": exit_counts,
                  "candidate_exit_counts": dict(candidate_counts),
                  "compared": len(records), "identical": len(records) - len(differences),
                  "differences": differences}
    else:
        controls = []
        for row in records:
            body = row["input"].removeprefix("quantum:").rstrip()
            if row.get("stderr", "").startswith("Unexpected notation") and body.endswith((",", ".")):
                adjusted = evaluate(args.worker, env, "$" + body[:-1] + "$")
                controls.append({"parent": row["id"], "removed": body[-1], **adjusted})
        report = {"trailing_punctuation_controls": controls, "source_sha256": index["current_sha256"],
                  "worker_sha256": worker_hash,
                  "mode": "Quantum, no authored bindings; only outer math delimiters removed",
                  "scope": "Exit zero records returned output. Correctness requires checking each expression in its lesson context.",
                  "exit_counts": exit_counts,
                  "records": records}
    args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

"""Replay the 168 source formulas and their recorded bindings for IBM-020."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--figure", type=Path, help="original Deutsch-Jozsa.svg")
    args = parser.parse_args()
    source = args.notebook.read_bytes()
    if hashlib.sha256(source).hexdigest() != "eb5801cde14e135802785c00092569b141deba7f3c091550b0ef0826654fc0a4":
        raise ValueError("Expected the pinned Deutsch–Jozsa notebook")
    if args.figure and hashlib.sha256(args.figure.read_bytes()).hexdigest() != "9362be98b328282f114d2825f34773020a91aa330973ada820f7ea36f78cbe81":
        raise ValueError("The circuit figure differs from the pinned image")
    cells = json.loads(source)["cells"]
    worker = args.worker.resolve()
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def evaluate(expr):
        result = subprocess.run([str(worker), "--json"], input=("quantum:" + expr).encode(),
                                env=env, timeout=30, capture_output=True, check=True)
        value = json.loads(result.stdout)
        if value["approximate"]:
            raise ValueError("Expected an exact result")
        return value["copy_text"]

    ledger = Path(__file__).with_name("ibm020-formula-audit.jsonl")
    lines = ledger.read_text(encoding="utf-8").splitlines()
    if len(lines) != 168:
        raise ValueError("Expected 168 formula occurrences")
    checks = 0
    for i, line in enumerate(lines, 1):
        row = json.loads(line)
        source = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        if row["id"] != i or row["literal"] != source or hashlib.sha256(source.encode()).hexdigest() != row["literal_sha256"]:
            raise ValueError(f"M{i:03}: source span differs")
        mode = "" if row["mode"] == "standard" else row["mode"]
        copy = evaluate(mode + source)
        if copy != row["copy"] or evaluate(mode + copy) != copy:
            raise ValueError(f"M{i:03}: unexpected Copy or re-entry")
        if "reference" in row and not ledger.with_name(row["reference"]).is_file():
            raise ValueError(f"M{i:03}: missing referenced evidence")
        for case in row.get("checks", []):
            expr = case.get("expression", "{copy}").replace("{copy}", copy)
            for key, value in case.get("bindings", []):
                expr = f"replace(({expr}),{key},{value})"
            if "scale" in case:
                expr = f"({case['scale']})*({expr})"
            actual = evaluate(expr)
            if actual != case["expected"]:
                raise ValueError(f"M{i:03}: expected {case['expected']}, got {actual}")
            checks += 1
    print(f"Verified {len(lines)} source formulas and {checks} bound results.")


if __name__ == "__main__":
    main()

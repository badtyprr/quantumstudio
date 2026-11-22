"""Replay the pinned Deutsch lesson against a built quantum worker."""
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
    parser.add_argument("--figures", type=Path, help="directory containing the two original circuit SVGs")
    args = parser.parse_args()
    if args.figures:
        for name, digest in [
            ("Deutsch-circuit.svg", "0121145c1b23f354ab31d93182376eb9a10057d6b2acf6754a32682866eec158"),
            ("Deutsch-circuit-states.svg", "a9de1c7f182892cab152c30ce1ff226d968bddf3375d59757d7278e0b370460f"),
        ]:
            if hashlib.sha256((args.figures / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Unexpected circuit figure {name}")
    worker = args.worker.resolve()
    source = args.notebook.read_bytes()
    if hashlib.sha256(source).hexdigest() != "e7dbe4d7175edf2376dc598021245b7308ac9d401fcb083b356b3072a06fef27":
        raise ValueError("Expected the pinned IBM-019 notebook")
    cells = json.loads(source)["cells"]
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def evaluate(expression):
        output = subprocess.run(
            [str(worker), "--json"], input=("quantum:" + expression).encode(),
            capture_output=True, env=env, timeout=30, check=True,
        )
        result = json.loads(output.stdout)
        if result["approximate"]:
            raise ValueError("Expected an exact result")
        return result["copy_text"]

    rows = Path(__file__).with_name("ibm019-formula-audit.jsonl").read_text(encoding="utf-8").splitlines()
    if len(rows) != 69:
        raise ValueError("Expected 69 math occurrences")
    checks = 0
    for index, line in enumerate(rows, 1):
        row = json.loads(line)
        text = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        if row["id"] != index or row["source"] != text or hashlib.sha256(text.encode()).hexdigest() != row["sha256"]:
            raise ValueError(f"M{index:03}: source span differs")
        copy = evaluate(row["mode"] + text)
        if copy not in (row["copy"], row.get("alternate_copy")) or evaluate(row["mode"] + copy) != copy:
            raise ValueError(f"M{index:03}: unexpected Copy or re-entry")
        for case in row["checks"]:
            expr = copy
            for symbol, value in case["bindings"]:
                expr = f"replace(({expr}),{symbol},{value})"
            actual = evaluate(expr)
            if actual.replace("−", "-") != case["expected"].replace("−", "-"):
                raise ValueError(f"M{index:03}: {case['bindings']} gave {actual}")
            checks += 1
    # Qiskit puts the measured top wire in the least significant position.
    circuit_checks = 0
    for table in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        permutation = [2 * (target ^ table[key]) + key for target in range(2) for key in range(2)]
        gate_rows = [",".join(str(int(r == dest)) for dest in permutation) for r in range(4)]
        gate = "[" + ";".join(gate_rows) + "]"
        prepared = "(H @ H)*|10>"
        queried = f"{gate}*({prepared})"
        final = f"(I @ H)*({queried})"
        signs = [(-1) ** (target ^ table[key]) for target in range(2) for key in range(2)]
        parity = table[0] ^ table[1]
        measured = [(-1) ** (target ^ table[0]) * int(key == parity) for target in range(2) for key in range(2)]
        for state, amplitudes, divisor in [
            (prepared, [1, 1, -1, -1], "2"), (queried, signs, "2"), (final, measured, "sqrt(2)"),
        ]:
            column = "[" + ";".join(map(str, amplitudes)) + "]"
            if evaluate(f"({state})=({column}/{divisor})") != "1":
                raise ValueError(f"Unexpected intermediate state for {table}")
            circuit_checks += 1
        for bit in (0, 1):
            probability = evaluate(f"norm((I @ <{bit}|)*({final}))^2")
            if probability != str(int(bit == parity)):
                raise ValueError(f"Unexpected probability for {table}, outcome {bit}")
            circuit_checks += 1
    print(f"Passed {len(rows)} source formulas, {checks} binding checks and {circuit_checks} circuit checks")


if __name__ == "__main__":
    main()

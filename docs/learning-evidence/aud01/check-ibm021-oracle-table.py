"""Check the original Simon table, its promise and its reversible native oracle."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("notebook", "worker", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raw = args.notebook.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if source_hash != "2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a":
        raise ValueError("Unexpected IBM-021 notebook")
    cell, = json.loads(raw)["cells"]
    literal = "".join(cell["source"])[2801:2993]
    if hashlib.sha256(literal.encode()).hexdigest() != "178a169c38d70f2e4e6d35ecf1dff50622aa03432ca650f361d716e8f140e867":
        raise ValueError("Source occurrence M029 changed")

    def evaluate(expr):
        proc = subprocess.run([args.worker, "--json"], input=("quantum:" + expr).encode(),
                              capture_output=True, timeout=120)
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode().strip())
        result = json.loads(proc.stdout)
        if result["approximate"]:
            raise ValueError("Expected an exact result")
        return result

    graph = evaluate(literal)["copy_text"]
    if evaluate(graph)["copy_text"] != graph:
        raise ValueError("Function graph changed on copy")
    expected = ["10011","00101","00101","10011","11010","00001","00001","11010"]
    values = []
    for x, bits in enumerate(expected):
        call = f"replace(f({x:03b}),f,{graph})"
        index = int(bits, 2)
        if evaluate(call)["copy_text"] != f"qbitlabel({index},5)":
            raise ValueError(f"Wrong five-bit output at {x:03b}")
        values.append(int(evaluate(f"bitvalue({call})")["copy_text"]))
    periods = {a ^ b for a in range(8) for b in range(a) if values[a] == values[b]}
    if periods != {3} or not all(values[a] == values[a ^ 3] for a in range(8)):
        raise ValueError("Simon promise failed")
    matrix = evaluate("oracle(vector(" + ",".join(map(str, values)) + "),5)")
    if (matrix["rows"], matrix["columns"]) != (256, 256):
        raise ValueError("Expected an eight-qubit oracle")
    for col in range(256):
        target = col ^ values[col >> 5]
        if any(row[col] != str(int(r == target)) for r, row in enumerate(matrix["cells"])):
            raise ValueError(f"Wrong permutation in column {col}")

    # Apply input-register Hadamards before and after the checked permutation
    # on a zero output register. Sum squared amplitudes over every output word.
    probabilities = []
    for y in range(8):
        signed_counts = [0] * 32
        for x in range(8):
            signed_counts[values[x]] += (-1)**((x & y).bit_count())
        prob = sum(Fraction(count, 8)**2 for count in signed_counts)
        if prob != (Fraction(1, 4) if (y & 3).bit_count() % 2 == 0 else 0):
            raise ValueError(f"Wrong probability for {y:03b}")
        probabilities.append(str(prob))
    report = dict(source_revision="3909abfe0218767141429e2beb52201fe4ba8ea4",
                  source_sha256=source_hash, cell_id=cell["id"], occurrence="M029",
                  source_literal=literal, worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  graph=graph, outputs=expected, nonzero_period="011", oracle_entries_checked=256**2,
                  probabilities_by_input_register_value=probabilities,
                  method="Evaluated the original display, queried all inputs, and checked every entry of the resulting native oracle. Independently summed signed amplitudes for the Simon circuit using this table.")
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

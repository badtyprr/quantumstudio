"""Check the two IBM-020 source interpretations against finite binary witnesses."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    def evaluate(expression):
        result = subprocess.run([args.worker, "--json"], input=("quantum:" + expression).encode(),
                                check=True, capture_output=True, timeout=30)
        response = json.loads(result.stdout)
        if response["approximate"]:
            raise ValueError(f"Expected exact output for {expression}")
        return response["copy_text"]

    source = json.loads((HERE / "ibm020-literal-results.json").read_bytes())
    literals = {r["id"]: r["input"].removeprefix("quantum:") for r in source["records"]}
    table_id = "R00-0-M013"
    relation_id = "R13-0-M047"
    table = evaluate("$$" + literals[table_id] + "$$")
    relation = evaluate("$" + literals[relation_id] + "$")
    if relation != "x = 0 || z = 0":
        raise ValueError("Re-audit the changed source relation")
    # A single scalar f cannot satisfy both f = 0 and f = 1/11.
    if table != r"\begin{gathered}1\\('f')==(0)\\('f')==(0)\\('f')==(1 ∕ 11)\end{gathered}":
        raise ValueError("Re-audit the changed oracle interpretation")
    rows = []
    for z in range(16):
        queries = [f"bitdot(bitstring({z},4),bitstring({x},4))=0" for x in range(16)]
        expected = [int((z & x).bit_count() % 2 == 0) for x in range(16)]
        expression = "vector(" + ",".join(queries) + ")"
        expected_copy = "vector(" + ",".join(map(str, expected)) + ")"
        if evaluate(expression) != expected_copy:
            raise ValueError(f"Explicit bit-string control failed for z={z}")
        mismatches = [x for x in range(16) if expected[x] != (x == 0 or z == 0)]
        rows.append(dict(z=z, expected=expected, literal_disagrees_for_x=mismatches))
    report = {"worker_sha256": hashlib.sha256(args.worker.read_bytes()).hexdigest(),
              "source_sha256": source["source_sha256"],
              "oracle": {"id": table_id, "literal": literals[table_id], "actual": table,
                         "expected": {"00": 0, "01": 0, "10": 0, "11": 1},
                         "finding": "Rows two and four impose contradictory values on the same scalar f."},
              "binary_dot": {"id": relation_id, "literal": literals[relation_id], "actual": relation,
                             "expected": "Even parity of the bitwise intersection of z and x.",
                             "explicit_control": "bitdot(bitstring(z,4),bitstring(x,4))=0",
                             "pairs_checked": 256, "literal_disagreements": sum(
                                 len(row["literal_disagrees_for_x"]) for row in rows), "rows": rows}}
    args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())


if __name__ == "__main__":
    main()

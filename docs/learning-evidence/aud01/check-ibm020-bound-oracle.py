"""Check IBM-020 source calls to f(x) against every two-bit Boolean function."""
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
    rows = json.loads((HERE / "ibm020-gui-corpus.json").read_bytes())["records"]
    source = {r["id"]: r["input"] for r in rows}
    identifiers = ["R13-0-M028", "R13-0-M029"]

    def exact(expression):
        process = subprocess.run([args.worker, "--json"], input=("quantum:" + expression).encode(),
                                 capture_output=True, check=True, timeout=30)
        answer = json.loads(process.stdout)
        if answer["approximate"]:
            raise ValueError("Expected an exact result")
        return answer

    for mask in range(16):
        entries = [f"f({x:02b}) & = {(mask >> x) & 1}" for x in range(4)]
        graph = exact(r"\begin{aligned}" + r"\\".join(entries) + r"\end{aligned}")["copy_text"]
        signs = [1 - 2*((mask >> x) & 1) for x in range(4)]
        for identifier in identifiers:
            body = source[identifier][2:-2].strip().removesuffix(".")
            body = body.replace(r"\Sigma^n", "bitstrings(2)")
            bound = f"replace(replace(({body}),f,{graph}),n,2)"
            if identifier == identifiers[0]:
                expected, scale = signs, "2*sqrt(2)"
            else:
                expected = [sum(signs[x] * (-1)**((x & y).bit_count()) for x in range(4)) for y in range(4)]
                scale = "4*sqrt(2)"
            result = exact(f"({scale})*({bound})")
            target = expected + [-v for v in expected]
            if result["cells"] != [[str(v).replace("-", "−")] for v in target]:
                raise ValueError(f"Amplitude mismatch for table {mask} at {identifier}")
    report = dict(worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  source_formulas={i: source[i] for i in identifiers},
                  truth_tables=16, state_columns=32, exact_amplitudes=256,
                  adaptation="Retained both source calls f(x). Bound f to the evaluated truth table, n to 2 and the query domain to bitstrings(2). Removed enclosing display delimiters and terminal punctuation for embedding.",
                  reference="The first column has signs from the truth table. The second has their Walsh coefficients. Both have the negative column in the output-qubit-one half.")
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

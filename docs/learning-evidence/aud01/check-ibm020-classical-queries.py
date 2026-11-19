"""Replay the finite classical-query comparisons in IBM-020, cell 0."""
import argparse
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from math import comb
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("worker", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    index = json.loads((HERE / "ibm020-inventory-map.json").read_bytes())
    raw = args.notebook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != index["current_sha256"]:
        raise ValueError("Notebook differs from the mapped revision")
    source = "".join(json.loads(raw)["cells"][0]["source"])
    formulas = {key: source[start + 1:end - 1] for key, start, end in index["cells"][0]["formulas"]
                if key.startswith("R00-7763-")}

    def exact(request):
        run = subprocess.run([args.worker, "--json"], input=request.encode(),
                             check=True, capture_output=True, timeout=30)
        result = json.loads(run.stdout)
        if result["approximate"]:
            raise ValueError(f"Approximate result for {request}")
        return Fraction(result["copy_text"].replace(" ∕ ", "/"))

    rows = []
    independent = {}
    for n in range(1, 5):
        size = 2**n
        half = size // 2
        worst = exact(f"quantum:replace({formulas['R00-7763-M001']},n,{n})")
        boundary = exact(f"quantum:replace({formulas['R00-7763-M003']},n,{n})")
        if (boundary, worst) != (half, half + 1):
            raise ValueError(f"Wrong deterministic boundary at width {n}")
        probabilities = []
        for k in range(1, size + 1):
            # Relabeling inputs maps any balanced function to this representative.
            errors = sum(all(x < half for x in subset) or all(x >= half for x in subset)
                         for subset in combinations(range(size), k))
            counted = Fraction(errors, comb(size, k))
            request = f"2*binomial({half},{k})/binomial({size},{k})"
            if exact(request) != counted or bool(counted) != (k < worst):
                raise ValueError(f"Distinct-query comparison failed at n={n}, k={k}")
            probabilities.append(str(counted))
            if k not in independent:
                observed = exact(f"quantum:replace({formulas['R00-7763-M014']},k,{k})")
                # Count ordered strings independently for each possible output bit.
                if observed != Fraction(2 * half**k, size**k):
                    raise ValueError(f"Independent-query comparison failed at k={k}")
                independent[k] = str(observed)
        rows.append(dict(n=n, deterministic_worst=int(worst), distinct_error_by_k=probabilities))

    success = 1 - Fraction(independent[11])
    threshold = exact("quantum:" + formulas["R00-7763-M016"]) / 100
    if not success > threshold:
        raise ValueError("The source percentage example failed")
    report = dict(source_sha256=index["current_sha256"],
                  worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  section="Cell 0, Classical difficulty",
                  source_inputs={key: formulas[key] for key in (
                      "R00-7763-M001", "R00-7763-M003", "R00-7763-M014", "R00-7763-M016")},
                  mode="Quantum replace bindings for source exponents; ordinary calculator binomial for distinct queries.",
                  rows=rows, independent_error_by_k=independent, first_k=1,
                  independent_success_at_11=str(success), source_success_threshold=str(threshold),
                  interpretation="The prose mentions different inputs. The displayed error expression is exact for independent draws with replacement. Distinct uniform inputs have a hypergeometric error probability, at most the displayed value. The deterministic threshold uses distinct inputs.")
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

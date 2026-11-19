"""Compare native classical oracle answers and the IBM-020 one-query circuit."""
import argparse
from functools import cache
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent


def classical_cost(ones, initial):
    @cache
    def cost(candidates):
        if candidates.bit_count() == 1:
            return 0
        partitions = ((candidates & mask, candidates & ~mask) for mask in ones)
        return 1 + min(max(cost(left), cost(right)) for left, right in partitions if left and right)

    optimum = cost(initial)
    return optimum, cost.cache_info().currsize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("notebook", "worker", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raw = args.notebook.read_bytes()
    receipt = json.loads((HERE / "ibm020-query-algorithms.json").read_bytes())
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("Unexpected notebook revision")
    cells = json.loads(raw)["cells"]
    namespace = {"display": lambda value: None}
    for index in (2, 8, 15):
        exec(compile("".join(cells[index]["source"]), f"<IBM-020 cell {index}>", "exec"), namespace)

    widths = []
    for n in range(1, 6):
        size = 1 << n
        ones = []
        for query in range(size):
            terms = [rf"bitstring({s},{n}) \cdot bitstring({query},{n})" for s in range(size)]
            expression = "quantum:vector(" + ",".join(terms) + ")"
            proc = subprocess.run([args.worker, "--json"], input=expression.encode(),
                                  check=True, capture_output=True, timeout=30)
            result = json.loads(proc.stdout)
            bits = [(s & query).bit_count() % 2 for s in range(size)]
            if result["approximate"] or result["copy_text"] != "vector(" + ",".join(map(str, bits)) + ")":
                raise ValueError(f"Native oracle disagrees at width {n}, query {query}")
            ones.append(sum(bit << s for s, bit in enumerate(bits)))

        for s in range(size):
            recovered = sum(((ones[1 << j] >> s) & 1) << j for j in range(n))
            if recovered != s:
                raise ValueError("Unit-vector queries did not reconstruct the secret")
            oracle = namespace["bv_query"](format(s, f"0{n}b"))
            # Keep the oracle as one named gate to count queries before decomposing it.
            gate = oracle.to_gate()
            gate.name = "bv_oracle"
            wrapped = QuantumCircuit(n + 1)
            wrapped.append(gate, range(n + 1))
            circuit = namespace["compile_circuit"](wrapped)
            if circuit.count_ops().get(gate.name, 0) != 1:
                raise ValueError("Unexpected oracle call count")
            state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
            expected = np.zeros(size)
            expected[s] = 1
            np.testing.assert_allclose(state.probabilities(range(n)), expected, rtol=0, atol=1e-12)
        optimum, states = classical_cost(ones, (1 << size) - 1)
        if optimum != n:
            raise ValueError(f"Unexpected classical worst-case optimum at width {n}")
        widths.append(dict(width=n, secrets=size, oracle_answers=size**2, quantum_calls=1,
                           optimal_classical_calls=optimum, candidate_sets_examined=states))
    report = dict(source_sha256=receipt["sha256"], worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  sections=["Cell 13: Classical difficulty", "Cell 18: base-case comparison"],
                  method="For each possible classical query, compare native typed dot products to independent bit parity. Minimize worst-case remaining calls over every informative query at every reachable candidate set. Reconstruct each secret with unit-vector queries. Count the wrapped source oracle in the compiled circuit and check its full output distribution.",
                  scope="Exact classical identification for all secrets. Finite base cases only; recursive Fourier sampling is outside this replay.",
                  widths=widths)
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

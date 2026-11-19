"""Replay all finite IBM-020 circuits using the pinned lesson and native worker.

Supply the importer's Python interpreter, the QIR adapter, and the worker.
Configure PATH and QALCULATE_DEFINITIONS_DIR for the supplied worker.
"""
import argparse
import base64
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import numpy as np
from qiskit import qasm3
from qiskit.quantum_info import Operator
import sympy

HERE = Path(__file__).resolve().parent
IMPORTER = HERE.parents[2] / "windows" / "qasm-import.py"


def run(command, payload):
    result = subprocess.run(command, input=payload, stdout=subprocess.PIPE,
                            check=True, timeout=120)
    return result.stdout


def native_case(circuit, expected, case, args):
    qasm = qasm3.dumps(circuit).encode()
    document = run([args.import_python, "-E", "-s", "-B", IMPORTER, "--classical"], qasm)
    pack = json.loads(run([args.adapter], document))
    response = json.loads(run([args.worker, "--exact-circuit"], base64.b64decode(pack["exact"])))
    probabilities = response["probabilities"]
    if not probabilities or not probabilities.keys() <= expected.keys():
        raise ValueError(f"Unexpected output states in {case}")
    errors = []
    for bits, ideal in expected.items():
        value = sympy.sympify(probabilities.get(bits, "0"), locals={"i": sympy.I})
        errors.append(abs(complex((value - ideal).evalf(50))))
    if not all(error < 1e-12 for error in errors):
        raise ValueError(f"{case} probability error {max(errors)}")
    return dict(case=case, max_probability_error=max(errors),
                qasm_sha256=hashlib.sha256(qasm).hexdigest(), probabilities=probabilities)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("notebook", "import_python", "adapter", "worker", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    evidence = json.loads((HERE / "ibm020-query-algorithms.json").read_bytes())
    raw = args.notebook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
        raise ValueError("Notebook bytes differ from the audited source")
    namespace = {"display": lambda obj: None}
    np.random.seed(1920)
    cells = json.loads(raw)["cells"]
    for index in evidence["executed"]:
        code = "".join(cells[index]["source"])
        exec(compile(code, f"<IBM-020 cell {index}>", "exec"), namespace)

    results = []
    for record in evidence["dj"]:
        np.random.seed(record["seed"])
        oracle = namespace["dj_query"](3)
        truth = tuple(map(int, record["truth"]))
        matrix = np.zeros((16, 16))
        for x in range(16):
            matrix[x ^ (truth[x % 8] << 3), x] = 1
        np.testing.assert_allclose(Operator(oracle).data, matrix, rtol=0, atol=1e-12)
        expected = {}
        for y in range(8):
            coefficient = sum((-1)**(bit + (x & y).bit_count()) for x, bit in enumerate(truth))
            expected[f"{y:03b}"] = Fraction(coefficient, 8)**2
        circuit = namespace["compile_circuit"](oracle)
        results.append(native_case(circuit, expected, "DJ " + record["truth"], args))

    for secret in evidence["bv"]:
        circuit = namespace["compile_circuit"](namespace["bv_query"](secret))
        expected = {f"{x:04b}": int(f"{x:04b}" == secret) for x in range(16)}
        results.append(native_case(circuit, expected, "BV " + secret, args))
    wanted = {"DJ " + f"{x:08b}" for x in range(256) if x.bit_count() in (0, 4, 8)}
    wanted.update("BV " + f"{x:04b}" for x in range(16))
    if len(results) != len(wanted) or {r["case"] for r in results} != wanted:
        raise ValueError("Incomplete native circuit coverage")
    evidence["native"] = results
    evidence["native_worker_sha256"] = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    evidence["checks"]["native"] = ("Exported every listed circuit through OpenQASM 3 and "
        "qasm-import.py, then ran the adapter payload with quantum-worker --exact-circuit. "
        "Compared all outcome probabilities with squared Walsh coefficients or the secret "
        "at 50 digits with absolute tolerance 1e-12. The importer lowers pi/8 to a decimal.")
    args.output.write_bytes((json.dumps(evidence, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

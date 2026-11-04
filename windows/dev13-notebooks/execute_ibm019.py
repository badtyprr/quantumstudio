"""Pinned IBM-019 notebook contract; external kernel, no QuantumStudio adapter."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile

SOURCE_SHA = "c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f"
CODE_CELLS = [2, 3, 5, 7, 9, 11, 13, 15]
WITNESS = '''import json, sys
import numpy as np
from qiskit.quantum_info import Statevector
checks = []
for case, truth in [(1, (0, 0)), (2, (0, 1)), (3, (1, 0)), (4, (1, 1))]:
    oracle = deutsch_function(case)
    # Independent definition: |x,y> maps to |x,y xor f(x)>.
    for x in (0, 1):
        for y in (0, 1):
            basis = x + 2*y
            expected_basis = x + 2*(y ^ truth[x])
            actual = Statevector.from_int(basis, 4).evolve(oracle).data
            expected = np.zeros(4); expected[expected_basis] = 1
            if not np.allclose(actual, expected, atol=1e-12, rtol=0):
                raise AssertionError((case, x, y, actual))
    expected_bit = truth[0] ^ truth[1]
    circuit = compile_circuit(oracle)
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    expected_state = np.zeros(4, dtype=complex)
    expected_state[expected_bit] = (-1)**truth[0] / np.sqrt(2)
    expected_state[expected_bit + 2] = -expected_state[expected_bit]
    residual = float(np.max(np.abs(state.data - expected_state)))
    if residual > 1e-12: raise AssertionError((case, state.data, expected_state))
    probabilities = state.probabilities([0])
    expected = [1-expected_bit, expected_bit]
    if not np.allclose(probabilities, expected, atol=1e-12, rtol=0):
        raise AssertionError((case, probabilities))
    counts = AerSimulator().run(circuit, shots=256, seed_simulator=1731).result().get_counts()
    if counts != {str(expected_bit): 256}: raise AssertionError((case, counts))
    label = deutsch_algorithm(oracle)
    if label != ('balanced' if expected_bit else 'constant'): raise AssertionError(label)
    checks.append(dict(case=case, truth=list(truth), state_residual=residual, probabilities=probabilities.tolist(), counts=counts, label=label))
errors = []
for invalid in (0, 5):
    try: deutsch_function(invalid)
    except ValueError as error: errors.append(dict(input=invalid, type=type(error).__name__, message=str(error)))
    else: raise AssertionError('invalid case accepted')
print(json.dumps(dict(checks=checks, expected_errors=errors, kernel_executable=sys.executable, kernel_version=sys.version)))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("SOURCE_HASH_MISMATCH")
    source = json.loads(raw)
    if len(source["cells"]) != 17 or [i for i, c in enumerate(source["cells"]) if c["cell_type"] == "code"] != CODE_CELLS:
        raise ValueError("SOURCE_CELL_CONTRACT_MISMATCH")
    lock = Path(__file__).with_name("ibm019-requirements.lock")
    packages = {}
    for line in lock.read_text().splitlines():
        requirement = line.split()[0]
        name, version = requirement.split("==")
        actual = importlib.metadata.version(name)
        if actual != version: raise ValueError(f"DEPENDENCY_MISMATCH: {name} {actual} != {version}")
        packages[name] = actual
    args.output.mkdir(parents=True, exist_ok=False)
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import AsyncKernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    notebook = nbformat.reads(raw.decode("utf-8"), as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code": cell.outputs = []; cell.execution_count = None
    notebook.cells.append(nbformat.v4.new_code_cell(WITNESS, metadata={"tags": ["authored-independent-witness"]}))
    report = dict(source_sha256=SOURCE_SHA, route="unchanged source cells in external notebook kernel plus separately marked authored witness",
                  python=sys.version, executable=sys.executable, packages=packages, source_cells=17, code_cells=CODE_CELLS,
                  authored_cell=17, lock_sha256=hashlib.sha256(lock.read_bytes()).hexdigest(), passed=False)
    with tempfile.TemporaryDirectory(prefix="ibm019-kernel-") as temp:
        kernels = Path(temp)/"kernels"; spec = kernels/"contract"; spec.mkdir(parents=True)
        (spec/"kernel.json").write_text(json.dumps(dict(argv=[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],
            display_name="Pinned IBM019 contract", language="python", env={"MPLBACKEND":"module://matplotlib_inline.backend_inline"})))
        manager = AsyncKernelManager(kernel_name="contract", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
        client = NotebookClient(notebook, km=manager, timeout=120, allow_errors=False,
                                resources={"metadata":{"path":str(args.output.resolve())}})
        try:
            client.execute(cleanup_kc=True)
            for i in range(17):
                if notebook.cells[i].source != "".join(source["cells"][i]["source"]): raise AssertionError("Source cell changed")
            if [notebook.cells[i].execution_count for i in CODE_CELLS] != list(range(1,9)):
                raise AssertionError("Original code execution order mismatch")
            for i in (7,11):
                if not any(o.get("data",{}).get("image/png") for o in notebook.cells[i].outputs):
                    raise AssertionError(f"Missing original drawing at cell {i}")
            if not any(o.get("data",{}).get("text/plain") == "'balanced'" for o in notebook.cells[15].outputs):
                raise AssertionError("Original algorithm output mismatch")
            text = "".join(o.get("text", "") for o in notebook.cells[17].outputs if o.output_type == "stream")
            report["independent_results"] = json.loads(text)
            if Path(report["independent_results"]["kernel_executable"]).resolve() != Path(sys.executable).resolve():
                raise AssertionError("Unexpected notebook interpreter")
            report["passed"] = True
        except Exception as error:
            report["error"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            nbformat.write(notebook, args.output/"executed.ipynb")
            report["cells"] = [dict(index=i, type=c.cell_type, source_sha256=hashlib.sha256(c.source.encode()).hexdigest(),
                execution_count=c.get("execution_count"), output_types=[o.output_type for o in c.get("outputs",[])]) for i,c in enumerate(notebook.cells)]
            (args.output/"result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("PASS: eight unchanged code cells and separately marked independent Deutsch witnesses.")


if __name__ == "__main__": main()

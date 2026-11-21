"""Replay the basis, amplitude and angle conventions in IBM-098 with local Qiskit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np
import qiskit
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
source = args.notebook.read_bytes()
if hashlib.sha256(source).hexdigest() != "09806407d3d3d6c7cc24de5f6ea0fd6a0a101f04b37fb8fcfc7eeaafeb2bc2a9":
    raise ValueError("The notebook differs from the audited revision")
cells = json.loads(source)["cells"]
worker = args.worker.resolve()
checks = []


def check(formula, expected="1"):
    result = subprocess.run([worker, "--json"], input=("quantum:" + formula).encode(),
                            capture_output=True, timeout=40, check=True,
                            env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data")))
    value = json.loads(result.stdout)
    assert value["copy_text"] == expected and not value["approximate"], (formula, value)
    checks.append(formula)


basis = []
for cell, values in [(3, (5, 7, 0)), (4, (4, 8, 5))]:
    text = "".join(cells[cell]["source"])
    assert "enumerate(all_bits)" in text and "qc.x(idx)" in text
    for var, value in zip("xyz", values):
        assert f"{var} = {value} " in text
    bits = "".join(f"{value:04b}" for value in values)
    qc = QuantumCircuit(len(bits))
    for wire, bit in enumerate(bits):
        if bit == "1":
            qc.x(wire)
    ket = Statevector.from_instruction(qc).probabilities_dict()
    assert ket == {bits[::-1]: 1.0} and bits != bits[::-1]
    # The worker's ket labels also put the most significant bit on the left.
    for label in (bits[::-1], bits):
        check(f"|{label}>", f"qketstate(qbitlabel({int(label, 2)},12))")
    basis.append(dict(features=values, wire_order=bits, ket_label=bits[::-1]))

weights = [4, 8, 5, 0]
qc = QuantumCircuit(2)
qc.initialize(np.array(weights) / np.sqrt(105), [0, 1])
np.testing.assert_allclose(Statevector.from_instruction(qc).data, np.array(weights)/np.sqrt(105), atol=1e-12)
state = "((4*|00>+8*|01>+5*|10>)/sqrt(105))"
check(f"probs({state})==[16/105;64/105;25/105;0]")
check(f"probs({state})==[16/105;25/105;64/105;0]", "0")
qc = QuantumCircuit(1)
qc.ry(np.pi/2, 0)
np.testing.assert_allclose(Statevector.from_instruction(qc).data, [2**-0.5]*2, atol=1e-12)
check("Ry(pi/2)*|0>==|+>")
check("Ry(pi/2)*|0>==|->", "0")
print(json.dumps(dict(source_sha256=hashlib.sha256(source).hexdigest(), qiskit=qiskit.__version__,
                      worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), basis=basis,
                      exact_worker_checks=checks), indent=2))

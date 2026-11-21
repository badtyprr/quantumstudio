"""Check the six-spin Lie and Suzuki circuits in the pinned IBM-120 exercise."""
import argparse
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import Operator, SparsePauliOp
from qiskit.synthesis import LieTrotter, SuzukiTrotter

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
raw = args.notebook.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == "d3185448e3387a0d92d8e09abc2d7490c27a69cb8f6993ff8ffddc07ce5b0fd5"
cells = json.loads(raw)["cells"]
scope = dict(np=np, QuantumCircuit=QuantumCircuit, PauliEvolutionGate=PauliEvolutionGate,
             SparsePauliOp=SparsePauliOp, LieTrotter=LieTrotter, SuzukiTrotter=SuzukiTrotter)
for i in (7, 9, 11, 15, 24):
    tree = ast.parse("".join(cells[i]["source"]))
    if i in (15, 24):
        assert tree.body[-1].value.func.attr == "draw"
        tree.body.pop()
    with redirect_stdout(io.StringIO()):
        exec(compile(tree, f"cell-{i}", "exec"), scope)

basis = np.arange(64)
z = 1 - 2 * ((basis[:, None] >> np.arange(6)) & 1)
zz = z[:, :-1] * z[:, 1:]
terms = [(np.diag(pair), -0.2) for pair in zz.T]
terms.extend((np.diag(spin), -1.2 * np.sin(np.pi / 8)) for spin in z.T)
identity = np.eye(64)
terms.extend((identity[basis ^ (1 << q)], -1.2 * np.cos(np.pi / 8)) for q in range(6))
hamiltonian = sum(p * c for p, c in terms)
energies, vectors = np.linalg.eigh(hamiltonian)
initial = identity[:, int("001100", 2)]
times = scope["dt"] * np.arange(scope["num_timesteps"] + 1)
reference = vectors @ ((vectors.T @ initial)[:, None] * np.exp(-1j * energies[:, None] * times))

def observables(states):
    probabilities = abs(states) ** 2
    return np.vstack([(states.conj() * (hamiltonian @ states)).sum(axis=0).real,
                      z.mean(axis=1) @ probabilities, zz.mean(axis=1) @ probabilities])

stats = {}
curves = {}
for tag in ("lt", "st2"):
    circuit = scope["single_step_evolution_" + tag].decompose(reps=3)
    unitary = Operator(circuit).data
    factors = terms if tag == "lt" else terms + terms[::-1]
    dt = scope["dt"] if tag == "lt" else scope["dt"] / 2
    product = identity
    for pauli, coeff in factors:
        angle = coeff * dt
        product = np.cos(angle) * product - 1j * np.sin(angle) * (pauli @ product)
    np.testing.assert_allclose(unitary, product, atol=1e-12, rtol=0)
    states = [initial]
    for _ in times[1:]:
        states.append(unitary @ states[-1])
    values = observables(np.column_stack(states))
    curves[tag] = values
    errors = np.sqrt(np.mean((values - observables(reference)) ** 2, axis=1))
    stats[tag] = dict(depth=circuit.depth(), gates=len(circuit), nonlocal_gates=circuit.num_nonlocal_gates(),
                      rms_errors=dict(zip(("energy", "magnetization", "correlation"), errors.round(9))))
np.testing.assert_allclose(curves["lt"][1:], curves["st2"][1:], atol=1e-12, rtol=0)
report = dict(source_sha256=digest, qiskit=qiskit.__version__, times=len(times),
              matrix_entries_per_method=4096, methods=stats)
args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")

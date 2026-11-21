"""Replay IBM's eight sampled Krylov circuits and its selected-CI postprocessing locally."""
import argparse
import contextlib
import hashlib
import io
import json
from importlib.metadata import version
from pathlib import Path
import re

import ffsim
import ffsim.qiskit
import numpy as np
from pyscf import fci, lib
from qiskit import QuantumRegister, QuantumCircuit
from qiskit.circuit.library import CPhaseGate, XGate, XXPlusYYGate
from qiskit.primitives.containers import BitArray
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_addon_sqd.fermion import SCIResult, diagonalize_fermionic_hamiltonian
from qiskit_aer import AerSimulator
from scipy.linalg import expm

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook",type=Path)
parser.add_argument("output",type=Path)
args = parser.parse_args()
source = args.notebook.read_bytes()
inventory = json.loads(Path(__file__).with_name("ibm088-inventory.json").read_bytes())
assert hashlib.sha256(source).hexdigest()==inventory["source_sha256"]
blocks = [block for cell in json.loads(source)["cells"]
          for block in re.findall(r"^```python\s*\n(.*?)^```","".join(cell["source"]),re.M|re.S)]
assert len(blocks)==5
lib.num_threads(2)
# The published snippets elide the constants and the one-particle propagator.
parameters = dict(t=1.0,V=0.6,eps=-1.0,U=2.0,dt=0.12,impurity_index=0,n_modes=8)
ns = dict(globals(),**parameters)
def execute(code):
    with contextlib.redirect_stdout(io.StringIO()):
        exec(code,ns)
mapping, build, optimize, sample, analyze = blocks
before,marker,after = mapping.partition("free_fermion_evolution =")
assert marker
execute(before)
ns["Utar"] = expm(-1j*parameters["dt"]*ns["h1e"])
execute(marker+after)
execute(build)
assert len(ns["circuits"])==8 and all(c.num_qubits==16 for c in ns["circuits"])

sim = AerSimulator(method="statevector",max_parallel_threads=4)
ns["target"] = sim.target
execute(optimize[optimize.index("pass_manager ="):])
assert "shots=500" in sample
batch = sim.run(ns["isa_circuits"],shots=500,memory=True,seed_simulator=24).result()
assert batch.success
samples = [batch.get_memory(j) for j in range(8)]
for records in samples:
    assert len(records)==500
    assert all(len(word)==16 and word[:8].count("1")==word[8:].count("1")==4 for word in records)
ns.update(bit_array=BitArray.from_samples([word for records in samples for word in records]),
          nelec=(4,4),result_history=[])
execute(analyze)
energy = float(ns["result"].energy)
reference = float(fci.direct_spin1.kernel(ns["h1e"],ns["h2e"],8,(4,4),tol=1e-10)[0])
assert np.isfinite(energy) and energy>=reference-1e-8
assert ns["result_history"] and all(len(step)==3 for step in ns["result_history"])
report = dict(source_sha256=inventory["source_sha256"],backend="local Aer statevector simulator",
              supplied_example_parameters=parameters,shots_per_circuit=500,
              distinct_strings_per_circuit=[len(set(words)) for words in samples],
              samples_in_four_up_four_down_sector=4000,selected_ci_energy=energy,
              full_ci_ground_energy=reference,variational_gap=energy-reference,
              iterations=len(ns["result_history"]),packages={key:version(key) for key in
              ("qiskit","qiskit-aer","ffsim","pyscf","qiskit-addon-sqd")})
args.output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print("Verified eight 16-qubit circuits and 4,000 samples. Selected-CI energy:",energy,"full-CI energy:",reference)

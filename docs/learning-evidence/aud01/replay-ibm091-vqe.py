"""Run the two published Hamiltonians and the VQE optimization on local Aer."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

notebook,output=map(Path,sys.argv[1:])
raw=notebook.read_bytes()
inventory=json.loads(Path(__file__).with_name("ibm091-inventory.json").read_bytes())
assert hashlib.sha256(raw).hexdigest()==inventory["source_sha256"]
cells=json.loads(raw)["cells"]
ns={"local_backend":AerSimulator(method="statevector",seed_simulator=73,max_parallel_threads=2)}
np.random.seed(24)
def execute(i):
    tree=ast.parse("".join(cells[i]["source"]))
    if i==21:
        for node in tree.body:
            if isinstance(node,ast.Assign):
                name=ast.unparse(node.targets[0])
                if name=="service":
                    assert ast.unparse(node.value)=="QiskitRuntimeService()"
                    node.value=ast.copy_location(ast.Constant(None),node.value)
                elif name=="backend":
                    assert "service.least_busy" in ast.unparse(node.value)
                    node.value=ast.copy_location(ast.Name("local_backend",ast.Load()),node.value)
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(tree,f"IBM091-cell-{i}","exec"),ns)

for i in (3,5):
    execute(i)
four=float(min(ns["eigenvalues"]))
for i in (14,16,18,21,23,25,27,29,30):
    execute(i)
ground=float(min(ns["eigenvalues"]))
opt=ns["res"]
def exact(parameters):
    circuit=ns["ansatz"].assign_parameters(parameters)
    return float(Statevector.from_instruction(circuit).expectation_value(ns["hamiltonian"]).real)
first=exact(ns["x0"]);last=exact(opt.x)
assert ns["num_params"]==len(opt.x)
assert len(ns["cost_history_dict"]["cost_history"])==opt.nfev<=50
assert ground-1e-10<=last<first and abs(last-opt.fun)<0.05
report=dict(source_sha256=inventory["source_sha256"],backend="local Aer via Runtime estimator",initial_seed=24,
    simulator_seed=73,requested_shots=10000,four_qubit_ground_energy=four,two_qubit_ground_energy=ground,
    exact_initial_energy=first,exact_final_energy=last,sampled_final_energy=float(opt.fun),
    evaluations=int(opt.nfev),optimizer_message=str(opt.message),parameters=opt.x.tolist())
output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print("VQE exact energies at initial and final parameters:",first,last,"ground:",ground)

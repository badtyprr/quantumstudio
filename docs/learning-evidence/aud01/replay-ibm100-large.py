"""Replay the 36-qubit classifier with its published initial weights and a local simulator."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import SparsePauliOp,Statevector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path);p.add_argument("report",type=Path)
a=p.parse_args()
raw=a.notebook.read_bytes()
digest=sha256(raw).hexdigest()
assert digest=="1f86ee572a58afff7ba19c7e5f91eb2a0b1e48b1b4b3ae828cd36b678032aad7"
cells=json.loads(raw)["cells"];env={}
def source(i):return "".join(cells[i]["source"])
for i in (55,57,60,61,63,67):
    exec(compile(source(i),f"QNN cell {i}","exec"),env)
tree=ast.parse(source(77))
weights=next(x.value for x in tree.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=="weight_params")
initial=np.array(ast.literal_eval(weights.args[0]))
assert len(initial)==72 and len(env["train_images"])==7
circ=env["full_circuit"];obs=env["observable"]
sim=AerSimulator(method="matrix_product_state",max_parallel_threads=2)
measured=circ.copy()
measured.save_expectation_value(obs,measured.qubits,label="parity")
compiled=transpile(measured,sim,optimization_level=1,seed_transpiler=24)
def forward(features,weights):
    circuits=[compiled.assign_parameters([*row,*weights]) for row in features]
    result=sim.run(circuits).result()
    assert result.success
    return np.array([float(result.data(i)["parity"]) for i in range(len(circuits))])
losses=[]
def cost(weights):
    preds=forward(env["train_images"],weights)
    loss=float(np.mean((preds-env["train_labels"])**2))
    losses.append(loss)
    return loss
fit=minimize(cost,initial,method="COBYLA",options={"maxiter":20})
test=forward(env["test_images"],fit.x)
assert np.isfinite(test).all() and np.isclose(fit.fun,min(losses))
# The source connects only horizontal neighbours. Independently compute
# each six-qubit row's exact parity and multiply the six expectations.
bound=circ.assign_parameters([*env["test_images"][0],*fit.x])
flat=transpile(bound,basis_gates=["u","cx"],optimization_level=0)
blocks=[QuantumCircuit(6) for _ in range(6)]
for gate in flat.data:
    if gate.operation.name=="barrier":continue
    indices=[flat.find_bit(q).index for q in gate.qubits]
    block=indices[0]//6
    assert all(q//6==block for q in indices)
    blocks[block].append(gate.operation,[q%6 for q in indices])
independent=float(np.prod([Statevector.from_instruction(row).expectation_value(SparsePauliOp("Z"*6)).real for row in blocks]))
assert np.isclose(independent,test[0],atol=1e-10)
report=dict(notebook_sha256=digest,backend="Aer matrix product state",qubits=36,initial_weights=72,
    train_images=7,test_images=3,requested_maxiter=20,optimizer_evaluations=int(fit.nfev),
    initial_loss=losses[0],best_loss=float(fit.fun),test_expectations=test.tolist(),
    test_labels=env["test_labels"],test_accuracy=float(np.mean(np.where(test>=0,1,-1)==env["test_labels"])),
    independent_first_test_parity=independent)
a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")

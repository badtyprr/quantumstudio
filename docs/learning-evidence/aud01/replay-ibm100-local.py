"""Verify both source QNN classifiers on the published 140/60 local split."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import numpy as np
from qiskit.quantum_info import Statevector

parser=argparse.ArgumentParser()
parser.add_argument("notebook",type=Path)
parser.add_argument("report",type=Path)
args=parser.parse_args()
raw=args.notebook.read_bytes()
digest=sha256(raw).hexdigest()
assert digest=="1f86ee572a58afff7ba19c7e5f91eb2a0b1e48b1b4b3ae828cd36b678032aad7"
cells=json.loads(raw)["cells"]
env={}
def run(index):
    exec(compile("".join(cells[index]["source"]),f"QNN lesson cell {index}","exec"),env)

for i in (2,4,10,12,14,16,18,20,22,24,26):
    run(i)
assert len(env["train_images"])==140 and len(env["test_images"])==60
report=[]
for model,fit,training,testing in [("first",34,36,38),("revised",47,51,52)]:
    if model=="revised":
        run(45)
    run(fit)
    run(training)
    train_accuracy=float(env["accuracy"])
    run(testing)
    test_accuracy=float(env["accuracy"])
    losses=np.array(env["objective_func_vals"])
    assert np.isfinite(losses).all() and losses.min()<losses[0]
    params=np.concatenate([env["test_images"][0],env["res"]["x"]])
    state=Statevector.from_instruction(env["circuit"].assign_parameters(params))
    exact=state.expectation_value(env["observable"]).real
    assert np.isclose(exact,env["pred_test"][0])
    report.append(dict(model=model,qubits=env["circuit"].num_qubits,trained_weights=len(env["res"]["x"]),
        objective_evaluations=len(losses),initial_loss=float(losses[0]),best_loss=float(losses.min()),
        train_accuracy=train_accuracy,test_accuracy=test_accuracy,first_test_expectation=float(exact)))
args.report.write_text(json.dumps(dict(notebook_sha256=digest,optimizer="COBYLA",backend="StatevectorEstimator",
    training_images=140,test_images=60,models=report),indent=2)+"\n",encoding="utf8")

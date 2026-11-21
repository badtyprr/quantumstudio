"""Check the published H2 ground-state circuit and all ten geometry points locally."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import numpy as np
from qiskit.primitives import StatevectorEstimator
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import Statevector
from scipy.optimize import minimize

p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path);p.add_argument("report",type=Path)
a=p.parse_args()
raw=a.notebook.read_bytes()
digest=sha256(raw).hexdigest()
cells=json.loads(raw)["cells"];env={}
np.random.seed(24)
report=dict(notebook_sha256=digest,seed=24,code_cells=[])
def run(i,changes=()):
    s="".join(cells[i]["source"])
    for old,new in changes:
        assert s.count(old)==1,old
        s=s.replace(old,new)
    exec(compile(s,f"{a.notebook.name}:{i}","exec"),env)
    report["code_cells"].append(i)
def compare(op,ansatz,params):
    exact=float(np.linalg.eigvalsh(op.to_matrix())[0])
    state=Statevector.from_instruction(ansatz.assign_parameters(params))
    ideal=float(state.expectation_value(op).real)
    assert ideal>=exact-1e-7 and state.is_valid()
    return exact,ideal

env["backend"]=GenericBackendV2(num_qubits=4,seed=24)
if digest=="2047e9348a25dc9b11296a0d4638090409b68f629ffa06b3336256a00641c1bc":
    for i in (2,4,6,10,12,14,16):
        changes=[("BackendEstimatorV2(backend=backend_sim)",'BackendEstimatorV2(backend=backend_sim,options={"seed_simulator":24})')] if i==14 else []
        run(i,changes)
        if i==14:env["backend_sim"].set_options(max_parallel_threads=2)
    exact,ideal=compare(env["H"],env["ansatz"],env["res"].x)
    report.update(backend="AerSimulator calibrated from synthetic GenericBackendV2(seed=24)",qubits=env["H"].num_qubits,
        evaluations=int(env["res"].nfev),sampled_total_energy=float(env["res"].fun),ideal_total_energy=ideal,
        exact_ground_energy=exact,nuclear_repulsion=float(env["nuclear_repulsion"]))
elif digest=="dd8d2e4d69b27a513b2459334485069c212f9070db34992b2fe333ca92cb0510":
    for i in (1,3,5,7,9):
        run(i,[("service = QiskitRuntimeService()","")] if i==7 else [])
    from qiskit.transpiler import generate_preset_pass_manager
    env["pm"]=generate_preset_pass_manager(optimization_level=1,backend=env["backend"],seed_transpiler=24)
    env["local_estimator"]=StatevectorEstimator()
    points=[]
    def record_fit(fun,x0,args,**options):
        result=minimize(fun,x0,args=args,**options)
        exact,ideal=compare(env["H"],env["ansatz"],result.x)
        assert np.isclose(result.fun,ideal)
        points.append(dict(angstrom=float(env["xx"]),ground_energy=exact,variational_energy=ideal,
            initial_energy=float(fun(x0,*args)),evaluations=int(result.nfev)))
        return result
    env["minimize"]=record_fit
    run(16,[("BackendEstimatorV2(backend=backend_sim)","local_estimator")])
    assert len(points)==10 and all(v["variational_energy"]<=v["initial_energy"]+1e-8 for v in points)
    for point,electron_energy in zip(points,env["vqe_elec_energies_sim"]):
        point["variational_electronic_energy"]=float(electron_energy)
    report.update(backend="StatevectorEstimator with a four-qubit synthetic transpilation target",geometry=points)
else:raise ValueError("Expected the pinned H2 ground-state or geometry notebook")
a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")

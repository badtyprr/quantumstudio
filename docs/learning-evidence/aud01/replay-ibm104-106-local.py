"""Verify published cost functions and deflation on local Qiskit primitives."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.primitives import StatevectorSampler, StatevectorEstimator
from qiskit.quantum_info import Statevector

parser=argparse.ArgumentParser()
parser.add_argument("notebook",type=Path)
parser.add_argument("report",type=Path)
args=parser.parse_args()
raw=args.notebook.read_bytes()
digest=sha256(raw).hexdigest()
cells=json.loads(raw)["cells"]
env={"display":lambda figure:figure.canvas.draw()}
np.random.seed(24)
report=dict(notebook_sha256=digest,source_cells=[])
def run(i,changes=()):
    code="".join(cells[i]["source"])
    for old,new in changes:
        assert code.count(old)==1,old
        code=code.replace(old,new)
    exec(compile(code,f"{args.notebook.name}:{i}","exec"),env)
    report["source_cells"].append(i)
    plt.close("all")

if digest=="62108930aca4330587cb805357519f56cc57db2e1c651a5d2ad8e529f0a39e58":
    for i in (7,8,9,11,17,18,20,25,28,29,31,32,37,39):
        run(i,[("StatevectorSampler()","StatevectorSampler(seed=24)")] if i==11 else [])
        if i==11:
            exact=Statevector.from_instruction(env["original_circuit"]).expectation_value(env["H"]).real
            assert np.isclose(exact,env["estimator_expvals"][-1])
            assert abs(env["total_expval"]-exact)<0.15
            report.update(sampled_mean=float(env["total_expval"]),exact_mean=float(exact))
        if i==32:
            value=Statevector.from_instruction(env["ansatz"].assign_parameters(env["x0"])).expectation_value(env["hamiltonian"]).real
            assert np.isclose(value,env["cost"])
            report["qaoa_cost"]=float(value)
    phases=env["phases"]
    vals=StatevectorEstimator().run([(env["qc"],env["observables"],env["individual_phases"])]).result()[0].data.evs
    error=max(abs(vals+np.cos(phases)))
    assert len(vals)==50 and error<1e-12
    report.update(local_phase_sweep_points=50,max_phase_error=float(error))
elif digest=="ab0d6f7e093c1f04e6095fad2f4d4d651fd4e00aa35baf7f1e2dda220fa310ec":
    for i in (4,5,6,8,24,26,28,30,32,34,36):
        changes=[]
        if i==30:
            env["Sampler"]=StatevectorSampler
            changes=[("sampler = Sampler()","sampler = Sampler(seed=24)")]
        run(i,changes)
        if i==8:
            report["variational_ground_energy"]=float(env["result"].fun)
    states=[*env["prev_states"],env["ansatz"].assign_parameters(env["prev_opt_parameters"])]
    states=[Statevector.from_instruction(c) for c in states]
    spectrum=np.linalg.eigvalsh(env["observable"].to_matrix())
    raw_energies=[float(v.expectation_value(env["observable"]).real) for v in states]
    overlaps=[float(abs(states[i].inner(states[j]))**2) for i in range(3) for j in range(i)]
    assert len(states)==3 and all(spectrum[0]-1e-8<=e<=spectrum[-1]+1e-8 for e in raw_energies)
    assert max(overlaps)<0.2
    report.update(sampler="StatevectorSampler(seed=24)",exact_spectrum=spectrum.tolist(),
        penalized_objectives=list(map(float,env["eigenvalues"])),state_energies=raw_energies,squared_overlaps=overlaps)
else:
    raise ValueError("Expected one of the pinned cost-function or variational-deflation notebooks")
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")

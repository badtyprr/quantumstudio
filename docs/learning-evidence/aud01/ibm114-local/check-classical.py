"""Verify the external Tokyo lecture's MPS, stabilizer and joint Pauli examples."""
import hashlib
import json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
src=(root/"20240607_UTokyo_ClassicalSimulation_revised_0909.ipynb").read_bytes()
assert hashlib.sha256(src).hexdigest()=="2357f375c4bf8a6a159dd874b2e11bfe0df386050a78249073ed42db3b209790"
cells=json.loads(src)["cells"]
scope={}
def run(indices):
    for i in indices:
        code="".join(cells[i]["source"])
        code=code.replace("int(1e7)","65536").replace("Sampler(default_shots=n_shots)","Sampler(default_shots=n_shots,seed=7919)")
        exec("\n".join(l for l in code.splitlines() if ".draw(" not in l and l!="plt.show()"),scope)
run([3,5,6,10,16,18,27,32,40,41])
sv=scope["res"].S
bond=scope["result"].data(0)["mps2"][1][0]
np.testing.assert_allclose(sv,bond,atol=1e-12)
run([55])
labels=scope["result"].data(0)["clf_hcxcz"].to_labels(mode="S")
counts=scope["result"].get_counts()
from qiskit.quantum_info import StabilizerState, Pauli
state=StabilizerState(scope["result"].data(0)["clf_hcxcz"])
assert set(counts)=={"00","11"}
assert state.expectation_value(Pauli("XX"))==-1 and state.expectation_value(Pauli("ZZ"))==1
run([82,83,86,87,92,94])
np.testing.assert_allclose(scope["result_sim1"],scope["result_sim2"],atol=1e-12)
sample=np.array([scope["res_iz"],-scope["res_zz"],scope["res_zi"]])/scope["n_shots"]
np.testing.assert_allclose(scope["result_sim1"],sample,atol=.018)
(root/"classical-results.json").write_text(json.dumps(dict(singular_values=sv.tolist(),
    aer_bond=bond.tolist(),stabilizers=labels,counts=counts,exact=scope["result_sim1"].tolist(),
    simultaneous=scope["result_sim2"].tolist(),shots=scope["n_shots"],sampled=sample.tolist()),indent=2))

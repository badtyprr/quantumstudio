"""Execute pinned reference-state, ansatz and optimization examples with Qiskit."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

parser=argparse.ArgumentParser()
parser.add_argument("notebook",type=Path)
parser.add_argument("report",type=Path)
args=parser.parse_args()
raw=args.notebook.read_bytes()
digest=hashlib.sha256(raw).hexdigest()
lesson={
    "9861697637e56521556f55ab3154daaa6189f4addef838f4b79b5ec7347194f9":102,
    "19874a793666d2b129bb79b9250695273e7f921e6f6f958bb90adc126e131238":103,
    "5441242c22ad4d9d40950aab8abf1d2e6b00fcf3063b76ac3e5f08188b12bb3f":105,
}[digest]
np.random.seed(24)
env={"display":lambda figure:figure.canvas.draw()}
report=dict(lesson=lesson,notebook_sha256=digest,qiskit=version("qiskit"),code_cells=[])
for i,c in enumerate(json.loads(raw)["cells"]):
    if c["cell_type"]!="code":
        continue
    exec(compile("".join(c["source"]),f"IBM{lesson} cell {i}","exec"),env)
    report["code_cells"].append(i)
    if lesson==102:
        name={3:"qc",5:"qc",7:"reference_circuit",10:"zz_feature_map_reference"}[i]
        state=Statevector.from_instruction(env[name])
        probs=state.probabilities_dict()
        assert np.isclose(sum(probs.values()),1)
        if i==3:assert probs=={"001":1}
        if i==5:assert set(probs)=={"100","111"} and np.isclose(probs["100"],0.5)
        report.setdefault("probabilities",{})[str(i)]={k:float(v) for k,v in probs.items()}
    elif lesson==103 and i in (3,7,9,12,17,21):
        circs=env["circuits"] if i==3 else [env["vqc_ansatz" if i==21 else "ansatz"]]
        for circ in circs:
            params=np.linspace(0.1,0.9,circ.num_parameters)
            state=Statevector.from_instruction(circ.assign_parameters(params))
            assert state.is_valid()
            report.setdefault("ansatz_circuits",[]).append(dict(cell=i,qubits=circ.num_qubits,parameters=circ.num_parameters,depth=circ.decompose().depth()))
    elif lesson==105 and i in (6,11,13):
        result=env["result"]
        cost=env["cost_func_vqe"]
        obs=env["observable"]
        start=float(cost(env["x0"],env["ansatz"],obs,env["estimator"]))
        final=float(result.fun)
        exact=float(np.linalg.eigvalsh(obs.to_matrix())[0])
        independent=Statevector.from_instruction(env["ansatz"].assign_parameters(result.x)).expectation_value(obs).real
        assert np.isclose(final,independent) and exact-1e-8<=final<start
        report.setdefault("optimizers",{})[{6:"SLSQP",11:"BFGS",13:"COBYLA"}[i]]=dict(start=start,final=final,ground_energy=exact,evaluations=int(result.nfev))
    plt.close("all")
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")

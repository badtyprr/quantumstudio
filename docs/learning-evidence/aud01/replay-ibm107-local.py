"""Exercise the source VQE and Max-Cut examples against exact solutions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path);p.add_argument("report",type=Path)
a=p.parse_args()
raw=a.notebook.read_bytes()
digest=sha256(raw).hexdigest()
assert digest=="0e3777202516059dfac67212bcce290fda4e56db19b3d7f86e8306da3ea33ed0"
cells=json.loads(raw)["cells"]
np.random.seed(24)
env={"display":lambda f:f.canvas.draw()}
report=dict(notebook_sha256=digest,source_cells=[],vqe={})
for i,c in enumerate(cells):
    if c["cell_type"]!="code" or not (i<=39 or i>=95):
        continue
    code="".join(c["source"])
    if i==110:
        code=code.replace("StatevectorSampler()","StatevectorSampler(seed=24)")
    exec(compile(code,f"IBM107 cell {i}","exec"),env)
    report["source_cells"].append(i)
    if i in (14,27,32,35,39):
        result=env[{27:"ref_result",32:"x0_1_result",35:"x0_2_result"}.get(i,"result")]
        e=float(result.fun)
        exact=float(env["solution_eigenvalue"])
        assert exact-1e-8<=e
        report["vqe"][str(i)]=dict(energy=e,exact=exact,evaluations=int(result.nfev))
    plt.close("all")
assert abs(report["vqe"]["14"]["energy"]-report["vqe"]["14"]["exact"])<1e-5
cuts={}
for value in range(1<<env["n"]):
    bits=f'{value:0{env["n"]}b}'
    bits_le=list(map(int,bits[::-1]))
    cuts[bits]=sum(weight for u,v,weight in env["edges"] if bits_le[u]!=bits_le[v])
total=sum(env["counts"].values())
best=max(cuts.values())
best_shots=sum(n for b,n in env["counts"].items() if cuts[b]==best)
assert total>0 and best_shots>0
report["max_cut"]=dict(vertices=env["n"],optimal_cut=best,most_sampled_cut=cuts[env["binary_string"]],
    total_shots=total,optimal_shots=best_shots,sampled_mean_cut=sum(n*cuts[b] for b,n in env["counts"].items())/total,
    source_hamiltonian_plus_offset=float(env["eigenvalue"]+env["offset"]))
a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")


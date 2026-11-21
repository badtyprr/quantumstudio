"""Replay the NMR source locally on a frozen device calibration."""
import argparse,ast,hashlib,json,os
from pathlib import Path
os.environ.update(MPLBACKEND="Agg",QISKIT_PARALLEL="FALSE",OMP_NUM_THREADS="2")
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
import numpy as np
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path,nargs="?",default=root/"nmr-with-qiskit.ipynb")
p.add_argument("--output",type=Path)
args=p.parse_args()
src=args.notebook.read_bytes()
digest=hashlib.sha256(src).hexdigest()
revisions={
    "057fe876a3ed23e7bea2c8cea8370c76631577b94141189d65149584c86be2f4":"mod013-manila-results.json",
    "6a4b981e2fc80e42246a243b9007168c77d24274b49361444ea0f99903bb72b2":"mod013-updated-manila-results.json",
}
if digest not in revisions:raise ValueError("Expected a verified NMR notebook revision")
output=args.output or root/revisions[digest]
cells=json.loads(src)["cells"]
env=dict(backend=FakeManilaV2())
# Run the pinned SDK imports from the setup cell and supply the local backend.
# The remaining setup statements request a live device.
setup=ast.parse("".join(cells[4]["source"]))
imports=[n for n in setup.body if isinstance(n,ast.ImportFrom)]
assert imports and all(n.module.startswith("qiskit_ibm_runtime") for n in imports)
exec(compile(ast.Module(body=imports,type_ignores=[]),"MOD013-source-imports","exec"),env)
ran=[]
for i,c in enumerate(cells):
    if c["cell_type"]!="code" or i==4: continue
    code="".join(c["source"])
    if i==6:
        assert "USE_HARDWARE = True" in code
        code=code.replace("USE_HARDWARE = True","USE_HARDWARE = False").replace(
            "AerSimulator.from_backend(backend)","AerSimulator.from_backend(backend,seed_simulator=103,max_parallel_threads=2)")
        code=code.replace("optimization_level=1, backend=run_backend",'scheduling_method="alap", optimization_level=1, backend=run_backend')
    print("cell",i,flush=True)
    exec(compile(code,f"MOD013-cell-{i}","exec"),env)
    ran.append(i)
def peaks(signal,axis,targets):
    from scipy.signal import find_peaks
    maxima=find_peaks(signal)[0]
    picked=sorted(float(axis[k]) for k in sorted(maxima,key=lambda k:signal[k],reverse=True)[:len(targets)])
    np.testing.assert_allclose(picked,targets,atol=.26)
    return picked
rabi=max(abs(np.array(env["p1"])-np.sin(env["angles"]/2)**2))
assert rabi<.2
observed={k:float(env[k]) for k in ("T1_fit","T2_star","T2")}
assert all(np.isfinite(v) and v>0 for v in observed.values())
for key in ("fid_tr","fid2_tr"):
    assert len(env[key])==48 and np.isfinite(env[key]).all()
result=dict(source_sha256=digest,calibration=env["backend"].name,cells=ran,qubit=env["QUBIT"],ax_layout=env["AX_LAYOUT"],
    ax2_layout=env["AX2_LAYOUT"],rabi_max_error=rabi,fit_microseconds=observed,
    reported_us=dict(T1=env["T1_us"],T2=env["T2_us"]),
    ax_peaks_hz=peaks(env["spec"],env["freq"],[-7,-5,5,7]),
    ax2_peaks_hz=peaks(env["spec2"],env["freq2"],[-7,-5,4,6,8]),
    trotter_points=48,max_source_ax2_entangling_gates=94)
output.write_text(json.dumps(result,indent=2))

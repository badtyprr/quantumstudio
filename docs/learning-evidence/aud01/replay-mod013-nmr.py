"""Replay the NMR source locally on a frozen device calibration."""
import hashlib,json,os,sys
from pathlib import Path
os.environ.update(MPLBACKEND="Agg",QISKIT_PARALLEL="FALSE",OMP_NUM_THREADS="2")
from qiskit_ibm_runtime import SamplerV2 as Sampler, Batch
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
import numpy as np
root=Path(__file__).resolve().parent
src=(root/"nmr-with-qiskit.ipynb").read_bytes()
assert hashlib.sha256(src).hexdigest()=="057fe876a3ed23e7bea2c8cea8370c76631577b94141189d65149584c86be2f4"
cells=json.loads(src)["cells"]
env=dict(backend=FakeManilaV2(),Sampler=Sampler,Batch=Batch)
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
result=dict(calibration=env["backend"].name,cells=ran,qubit=env["QUBIT"],ax_layout=env["AX_LAYOUT"],
    ax2_layout=env["AX2_LAYOUT"],rabi_max_error=rabi,fit_microseconds=observed,
    reported_us=dict(T1=env["T1_us"],T2=env["T2_us"]),
    ax_peaks_hz=peaks(env["spec"],env["freq"],[-7,-5,5,7]),
    ax2_peaks_hz=peaks(env["spec2"],env["freq2"],[-7,-5,4,6,8]),
    trotter_points=48,max_source_ax2_entangling_gates=94)
(root/"mod013-manila-results.json").write_text(json.dumps(result,indent=2))

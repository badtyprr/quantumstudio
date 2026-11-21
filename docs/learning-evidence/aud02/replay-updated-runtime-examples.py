"""Execute source cells using the updated Runtime sampler on local simulators."""
import argparse,cmath,hashlib,json,math,os
from pathlib import Path
import numpy as np
os.environ.setdefault("MPLBACKEND","Agg")
os.environ.setdefault("QISKIT_PARALLEL","FALSE")
p=argparse.ArgumentParser()
p.add_argument("source_directory",type=Path)
p.add_argument("catalog_delta",type=Path)
p.add_argument("output",type=Path)
args=p.parse_args()
delta=json.loads(args.catalog_delta.read_bytes())
assert delta["current_revision"]=="079769d205eb3b60e077820060274c7b0359c123"
hashes={r["path"]:r["new_sha256"] for r in delta["modified"]}
def lesson(slug):
    path="learning/courses/utility-scale-quantum-computing/"+slug+".ipynb"
    raw=(args.source_directory/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==hashes[path]
    return json.loads(raw)["cells"]
def run(cells,indices,scope):
    for i in indices:
        code="".join(cells[i]["source"]).replace("AerSimulator()","AerSimulator(seed_simulator=1739,max_parallel_threads=2)")
        # Only the explicitly listed local cells are run. Keep the numerical
        # statements and original SDK calls and omit the display-only expressions.
        lines=[x for x in code.splitlines() if not x.lstrip().startswith(("plot_histogram(","qc.draw(","qpe.draw(","grover_circuit.draw("))]
        exec(compile("\n".join(lines),f"source-cell-{i}","exec"),scope)
def fourier(phase):
    return [abs(sum(cmath.exp(2j*math.pi*j*(phase-k/8)) for j in range(8))/8)**2 for k in range(8)]
tele=lesson("teleportation");v={}
run(tele,[3,7,9,10,13,14,15,17,18,19,21,25,26,28,32,34,36,41,43],v)
bloch=[float(v["r"+axis+"_approx"]) for axis in "xyz"]
np.testing.assert_allclose(bloch,[v["r"+axis] for axis in "xyz"],atol=.12)
counts=v["counts"];assert sum(counts.values())==v["nshots"] and len(counts)==4 and all(k[0]=="0" for k in counts)
run(tele,[72,74,75],v)
assert v["counts"]=={"11":1000}
report={"teleportation":counts,"bloch":bloch,"dense_coding":v["counts"],"grover":[],"phase":[]}
grover=lesson("grovers-algorithm");v={}
run(grover,[3,7,10,13,16,17,18,20],v)
counts=v["result"][0].data.meas.get_counts()
assert counts=={"001":sum(counts.values())}
report["grover"].append(counts)
for ids in [[38,39,40,42,43],[46,47,48,49],[52,53,54,55]]:
    run(grover,ids,v)
    counts=v["counts"]
    expected=math.sin((2*v["num_iterations"]+1)*math.asin(1/math.sqrt(8)))**2
    assert abs(counts.get("0111",0)/sum(counts.values())-expected)<.06
    report["grover"].append(counts)
phase=lesson("quantum-phase-estimation");v={}
for target,ids in [(1/8,[3,47,49,51,53,54,55,57]),(1/3,[63,64])]:
    run(phase,ids,v)
    counts=v["answer"];shots=sum(counts.values())
    assert max(abs(counts.get(f"{k:03b}",0)/shots-prob) for k,prob in enumerate(fourier(target)))<.04
    report["phase"].append(counts)
args.output.write_text(json.dumps(dict(revision=delta["current_revision"],results=report),indent=2)+"\n")

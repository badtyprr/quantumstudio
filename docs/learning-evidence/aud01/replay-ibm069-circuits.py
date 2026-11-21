"""Replay pinned IBM introductory circuits on a local Aer simulator."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2 as Sampler

root=Path(sys.argv[1])
report={}
def notebook(stem,checksum):
    data=(root/(stem+".ipynb")).read_bytes()
    assert hashlib.sha256(data).hexdigest()==checksum
    return json.loads(data)["cells"]

def execute(cells,indices,namespace):
    for i in indices:
        assert cells[i]["cell_type"]=="code"
        exec(compile("".join(cells[i]["source"]),f"notebook-cell-{i}","exec"),namespace)

def check_counts(counts,shots,expected):
    assert sum(counts.values())==shots and set(counts)==set(expected)
    assert all(abs(value/shots-0.5)<0.2 for value in counts.values())

def probabilities(circuit):
    return Statevector.from_instruction(circuit.remove_final_measurements(inplace=False)).probabilities_dict()

digests={}
for lesson in ("069","070","071"):
    inventory=json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    digests[Path(inventory["source"]).stem]=inventory["source_sha256"]
with contextlib.redirect_stdout(io.StringIO()):
    ns=dict(QuantumCircuit=QuantumCircuit,generate_preset_pass_manager=generate_preset_pass_manager,
            Sampler=Sampler,AerSimulator=AerSimulator,plot_histogram=plot_histogram)
    stem="build-and-run-your-first-quantum-program"
    cells=notebook(stem,digests[stem]);execute(cells,[4,7,9,14],ns)
    counts=ns["counts"];check_counts(counts,1000,["00","11"])
    report[stem]=dict(executed_cells=[4,7,9,14],shots=1000,counts=counts,backend="AerSimulator")
    stem="quantum-mechanics-basics"
    execute(notebook(stem,digests[stem]),[2],ns)
    probs=probabilities(ns["qc"]);assert set(probs)=={"00","11"} and all(abs(p-0.5)<1e-12 for p in probs.values())
    report[stem]=dict(executed_cells=[2],probabilities=probs)
    stem="your-first-quantum-experiment";cells=notebook(stem,digests[stem])
    ns["backend"]=AerSimulator.from_backend(GenericBackendV2(2,seed=137))
    ns["backend"].set_options(noise_model=None,seed_simulator=137,max_parallel_threads=1)
    order=[2,5,7,9,10,12,14,16,18,19,20,22]
    execute(cells,order,ns)
    counts=ns["counts"];check_counts(counts,100,["01","10"])
    exact=Statevector.from_instruction(ns["qc"]).expectation_value(ns["obs"]).real
    estimate=float(ns["res"][0].data.evs)
    assert abs(exact+1)<1e-12 and abs(estimate-exact)<0.1,(estimate,exact)
    report[stem]=dict(executed_cells=order,shots=100,counts=counts,estimator=estimate,
                      exact_energy=exact,backend="two-qubit local Aer simulator")
from importlib.metadata import version
report['versions']={name:version(name) for name in ('qiskit','qiskit-aer','qiskit-ibm-runtime')}
print(json.dumps(report,indent=2))

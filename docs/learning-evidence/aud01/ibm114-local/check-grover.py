"""Check each published Grover iteration count against amplitude amplification."""
import hashlib
import json
import math
from pathlib import Path
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

root = Path(__file__).resolve().parent
src = (root / "grovers-algorithm.ipynb").read_bytes()
assert hashlib.sha256(src).hexdigest() == json.loads((root / "notebooks.json").read_bytes())[3][2]
cells = json.loads(src)["cells"]
sim = AerSimulator(seed_simulator=9701)
scope = {}
def run(indices):
    for index in indices:
        src = "".join(cells[index]["source"])
        exec("\n".join(line for line in src.splitlines() if ".draw(" not in line), scope)

results = []
run([3,7,10,13])
for indices, target in [([16,17,18],"001"),([38,39,40,42],"0111"),([46,47,48],"0111"),([52,53,54],"0111")]:
    run(indices)
    qc = scope["grover_circuit"]
    if not qc.num_clbits:
        qc.measure_all()
    exact = Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities_dict()
    n = scope["n"]
    iterations = scope["num_iterations"]
    expected = math.sin((2*iterations+1)*math.asin(2**(-n/2)))**2
    assert abs(expected-exact[target])<1e-12
    counts = sim.run(qc,shots=8192).result().get_counts()
    observed = counts.get(target,0)/8192
    assert abs(observed-expected)<0.025
    assert all(label.startswith("0") for label in counts)
    results.append(dict(n=n,iterations=iterations,target=target,expected=expected,observed=observed,counts=counts))
(root / "grover-results.json").write_text(json.dumps(results,indent=2))

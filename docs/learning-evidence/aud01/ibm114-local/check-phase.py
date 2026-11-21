"""Execute the two simulator examples and compare with Fourier phase probabilities."""
import cmath
import hashlib
import json
import math
from pathlib import Path

root=Path(__file__).resolve().parent
src=(root/"quantum-phase-estimation.ipynb").read_bytes()
assert hashlib.sha256(src).hexdigest()==json.loads((root/"notebooks.json").read_bytes())[4][2]
cells=json.loads(src)["cells"]
scope={}
results=[]
for phase,indices in [(1/8,[3,47,49,51,53,54,55,57]),(1/3,[63,64])]:
    for index in indices:
        code="".join(cells[index]["source"])
        code=code.replace("AerSimulator()","AerSimulator(seed_simulator=9357)")
        exec("\n".join(l for l in code.splitlines() if not l.startswith(("qpe.draw(","plot_histogram("))),scope)
    counts=scope["answer"]
    shots=scope["shots"]
    expected=[abs(sum(cmath.exp(2j*math.pi*j*(phase-k/8)) for j in range(8))/8)**2 for k in range(8)]
    assert sum(counts.values())==shots
    assert max(abs(counts.get(f"{k:03b}",0)/shots-prob) for k,prob in enumerate(expected))<0.03
    if phase==1/8:
        assert counts=={"001":shots}
    results.append(dict(phase=phase,shots=shots,counts=counts,theory=expected))
(root/"phase-results.json").write_text(json.dumps(results,indent=2))

"""Replay both source layouts on the illustrated topology and propagate a six-wire observable."""
import hashlib,json,re
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Clifford,Pauli,Statevector
from qiskit.transpiler import CouplingMap
import numpy as np

root=Path(__file__).resolve().parent
src=(root/"modern-workflows.mdx").read_bytes()
assert hashlib.sha256(src).hexdigest()=="f6f8b127487d5050ed7b527bfec52fca4acdcdf4db09451458c6acb014aa3f25"
blocks=re.findall(r"\\begin\{aligned\}(.*?)\\end\{aligned\}",src.decode(),re.S)
assert len(blocks)==2
# Horizontal rows and vertical bridges visible in check-in-transp.avif.
edges=[(q,q+1) for start in (0,10,20) for q in range(start,start+7)]
edges += [(3,8),(8,13),(7,9),(9,17),(11,18),(18,21),(15,19),(19,25)]
topology=CouplingMap(edges);topology.make_symmetric()
qc=QuantumCircuit(6)
qc.h(0);qc.x(2);qc.h(4)
qc.cx(0,1);qc.cx(2,5);qc.cx(0,3);qc.x(4);qc.x(1);qc.cx(0,2);qc.cx(1,4)
records=[]
for block in blocks:
    pairs=[(int(a),int(b)) for a,b in re.findall(r"aq\[(\d+)\].*?tq\[(\d+)\]",block)]
    layout=dict(pairs)
    assert set(layout)==set(range(6)) and len(set(layout.values()))==6
    out=transpile(qc,coupling_map=topology,initial_layout=[layout[i] for i in range(6)],
        basis_gates=["h","x","cx","swap"],optimization_level=0,seed_transpiler=11)
    ops=dict(out.count_ops())
    assert ops.get("swap",0)==0 and ops["cx"]==5
    records.append(dict(layout=pairs,operations=ops))
ladder=QuantumCircuit(6)
for q in range(5):ladder.cx(q,q+1)
z5=Pauli("ZIIIII")
propagated=z5.evolve(Clifford(ladder),frame="h")
assert propagated.to_label()=="ZZZZZZ"
checks=[]
for seed in (3,5,7):
    rng=np.random.default_rng(seed)
    state=Statevector(rng.normal(size=64)+1j*rng.normal(size=64))
    state=Statevector(state.data/np.linalg.norm(state.data))
    before=state.expectation_value(propagated).real
    after=state.evolve(ladder).expectation_value(z5).real
    np.testing.assert_allclose(before,after,atol=1e-12)
    checks.append(dict(seed=seed,before=before,after=after))
(root/"ibm139-layout-observable.json").write_text(json.dumps(dict(layouts=records,pauli=propagated.to_label(),checks=checks),indent=2))

"""Compare the published dynamic teleportation circuit with an explicit inverse gate."""
import hashlib
import json
from pathlib import Path
from qiskit.circuit.library import UGate
from qiskit_aer import AerSimulator

root = Path(__file__).resolve().parent
src = (root / "teleportation.ipynb").read_bytes()
assert hashlib.sha256(src).hexdigest() == json.loads((root / "notebooks.json").read_bytes())[2][2]
cells = json.loads(src)["cells"]
def source(index):
    return "".join(cells[index]["source"])
def run(index, env, old="", new=""):
    code = source(index)
    if old:
        assert old in code
        code = code.replace(old, new)
    exec(code.replace('qc.draw(output="mpl")', 'pass'), env)

sim = AerSimulator(seed_simulator=8463)
def sample(qc):
    return sim.run(qc, shots=2048).result().get_counts()
results = []
for theta, phi in [(0.0,0.0),(1.11,0.73),(2.17,-1.31)]:
    env = dict(theta=theta,varphi=phi)
    for i in (25,26,28,32,34,36):
        run(i, env)
    original = env["qc"].copy()
    ref = original.copy()
    run(41,env)
    counts = sample(env["qc"])
    ref.append(UGate(theta,phi,0).inverse(),[2])
    ref.measure(2,2)
    corrected = sample(ref)
    assert all(s[0]=="0" for s in corrected) and len(corrected)==4
    results.append(dict(theta=theta,phi=phi,published=counts,explicit_inverse=corrected))
assert all(all(s[0]=="0" for s in r["published"]) and len(r["published"])==4 for r in results)
messages={}
for msg in ["00","01","10","11"]:
    env={}
    run(72,env)
    run(74,env,'msg = "11"',f'msg = "{msg}"')
    messages[msg]=sample(env["qc"])
    assert messages[msg]=={msg:2048}
(root/"teleportation-results.json").write_text(json.dumps(dict(teleportation=results,dense_coding=messages),indent=2))

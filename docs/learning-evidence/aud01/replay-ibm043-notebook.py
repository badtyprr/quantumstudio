"""Replay the ten original multiple-systems notebook cells and verify their tensor order."""
import argparse
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import subprocess

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
raw = args.notebook.read_bytes()
digest = sha256(raw).hexdigest()
assert digest == "971002d918d25f489f4b51e4a1bb1c8a675e5f220f6823a640517d77387bf840"
worker = args.worker.resolve()
scope = {}
ledger, measurements = [], []
w = np.array([0,1,1,0,1,0,0,0])/np.sqrt(3)
def display(value):
    assert value.data.strip()
    displays.append(type(value).__name__)
    if idx == 19:
        if len(displays) == 1:
            np.testing.assert_allclose(scope["w"].data, w)
            scope["w"].seed(4319)
        else:
            bits = len(displays)-1
            sampled = scope["result"]
            assert len(sampled) == bits
            indices = np.arange(len(w)) % (2**bits)
            projected = np.where(indices == int(sampled,2), w, 0)
            probability = np.vdot(projected,projected).real
            assert probability > 0
            np.testing.assert_allclose(scope["state"].data, projected/np.sqrt(probability))
            measurements.append(dict(bits=bits,outcome=sampled,probability=float(probability)))

scope["display"] = display
phi = np.array([1,-1j,1,-1j])/2
h = np.array([[1,1],[1,-1]])/np.sqrt(2)
flip = np.array([[0,1],[1,0]])
cells = json.loads(raw)["cells"]
for idx,cell in enumerate(cells):
    if cell["cell_type"]!="code":
        continue
    stdout, displays = StringIO(), []
    with redirect_stdout(stdout):
        exec(compile("".join(cell["source"]),cell["id"],"exec"),scope)
    if idx==5:
        np.testing.assert_allclose(scope["psi"].data,[0,1,0,0])
    if idx in (7,9):
        value = scope["phi"] if idx==7 else scope["plus"] ^ scope["minus_i"]
        np.testing.assert_allclose(value.data,phi)
    if idx in (11,13):
        hi = scope["H"].tensor(scope["Id"])
        np.testing.assert_allclose(hi.data,np.kron(h,np.eye(2)))
        operator = hi.tensor(scope["X"]) if idx==11 else scope["H"] ^ scope["Id"] ^ scope["X"]
        np.testing.assert_allclose(operator.data,np.kron(np.kron(h,np.eye(2)),flip))
    if idx==15:
        np.testing.assert_allclose(scope["phi"].evolve(scope["H"] ^ scope["Id"]).data,
                                   np.array([1,-1j,0,0])/np.sqrt(2),atol=1e-15)
    if idx==17:
        np.testing.assert_allclose(scope["psi"].evolve(scope["CX"]).data,np.array([1,0,0,1])/np.sqrt(2))
    ledger.append(dict(cell=idx,id=cell["id"],stdout=stdout.getvalue().strip(),displays=displays))
assert len(ledger)==10 and len(measurements)==2
expressions = ["(|0>@|1>)=[0;1;0;0]", "(|+>@|-i>)=([1;-i;1;-i]/2)",
               "(H@I)*(|+>@|-i>)=([1;-i;0;0]/sqrt(2))","CX*(|+>@|0>)=([1;0;0;1]/sqrt(2))"]
notation = json.loads(Path(__file__).with_name("ibm043-inventory.json").read_bytes())["rows"]
def calculate(expr):
    run = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,timeout=30,
                         check=True,env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    value=json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

action = calculate(notation[8]["literal"])
definition = calculate(notation[9]["literal"])
for state,expected in [("(|+>@|-i>)","1"), ("|00>","0")]:
    expressions.append(f'replace(({definition}),qketstate("φ"),{state})={expected}')
    expressions.append(f'(replace(({action}),qnamedket("φ"),{state})=([1;-i;0;0]/sqrt(2)))={expected}')
# Every source occurrence has an independent value or a state supplied by
# the surrounding notebook. The source reuses psi in two different cells.
ket_zero, ket_one = "[1;0]", "[0;1]"
plus, minus_i = "[1;1]/sqrt(2)", "[1;-i]/sqrt(2)"
bell = "[1;0;0;1]/sqrt(2)"
cx = "[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]"
values = {1: ket_zero, 2: ket_one, 4: ket_zero, 5: ket_one, 6: "1", 7: plus, 8: minus_i,
          11: cx, 14: cx, 15: bell}
definitions = {3: ("ψ", "[0;1;0;0]"), 10: ("φ", "[1;-i;1;-i]/2"),
               13: ("ψ", "[1;0;1;0]/sqrt(2)"), 16: ("w", "[0;1;1;0;1;0;0;0]/sqrt(3)")}
actions = {9: ("φ", "[1;-i;1;-i]/2", "[1;-i;0;0]/sqrt(2)"), 12: ("ψ", "[1;0;1;0]/sqrt(2)", bell)}
for ordinal, row in enumerate(notation, 1):
    text = "".join(cells[row["cell"]]["source"])
    assert text[row["start"]:row["end"]] == row["literal"]
    copied = calculate(row["literal"])
    if ordinal in values:
        expressions.append(f"({copied})=({values[ordinal]})")
    elif ordinal in definitions:
        label, state = definitions[ordinal]
        for probe, truth in [(state, "1"), ("|00>", "0")]:
            expressions.append(f'replace(({copied}),qketstate("{label}"),{probe})={truth}')
    else:
        label, state, expected = actions[ordinal]
        expressions.append(f'replace(({copied}),qnamedket("{label}"),({state}))=({expected})')
for expr in expressions:
    assert calculate(expr)=="1", expr
print(json.dumps(dict(source_sha256=digest,worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      qiskit=scope["__version__"],numpy=np.__version__,cells=ledger,
                      seed=4319,measurements=measurements,calculator_checks=expressions),indent=2))

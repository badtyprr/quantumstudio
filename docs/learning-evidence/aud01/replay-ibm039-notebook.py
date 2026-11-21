"""Replay the pinned single-qubit notebook, including its final display expressions."""
import argparse
import ast
from contextlib import redirect_stdout
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO, StringIO
import json
import math
import os
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
raw = args.notebook.read_bytes()
source = json.loads(Path(__file__).with_name("ibm039-inventory.json").read_bytes())
assert sha256(raw).hexdigest() == source["source_sha256"]
worker = args.worker.resolve()
cells = json.loads(raw)["cells"]
ledger, displays, samples = [], [], []
def display(value):
    if value is None:
        return
    if isinstance(value, matplotlib.figure.Figure):
        buf = BytesIO()
        value.savefig(buf,format="png")
        assert buf.getvalue().startswith(b"\x89PNG")
        displays.append("figure")
    else:
        assert str(getattr(value,"data",value)).strip()
        displays.append(type(value).__name__)

scope = {"display":display}
e = np.exp(1j*np.pi/4)
reference = np.array([(1-e)/2,1j*(1+e)/2])
for index,cell in enumerate(cells):
    if cell["cell_type"] != "code":
        continue
    code = "".join(cell["source"])
    tree = ast.parse(code)
    last = tree.body.pop().value if tree.body and isinstance(tree.body[-1],ast.Expr) else None
    displays.clear()
    stdout = StringIO()
    if index in (21,23,36):
        scope["v"].seed(3900+index)
    with redirect_stdout(stdout):
        exec(compile(tree,cell["id"],"exec"),scope)
        if last is not None:
            display(eval(compile(ast.Expression(last),cell["id"],"eval"),scope))
    if index == 9:
        assert np.allclose(scope["M"]@scope["M"],[[1,.75],[0,.25]])
    if index == 17:
        assert scope["u"].is_valid() and not scope["w"].is_valid()
    if index == 21:
        probabilities = scope["state"].probabilities()
        assert np.isclose(probabilities[int(scope["outcome"])],1)
    if index in (28,34):
        assert np.allclose(scope["v"].data,reference)
    if index in (23,36):
        shots,p0 = (1000,5/9) if index==23 else (4000,abs(reference[0])**2)
        counts = {k:int(v) for k,v in scope["statistics"].items()}
        assert sum(counts.values())==shots and abs(counts["0"]-shots*p0)<=6*math.sqrt(shots*p0*(1-p0))
        samples.append(dict(cell=index,seed=3900+index,counts=counts,expected_zero=float(p0)))
    ledger.append(dict(cell=index,id=cell["id"],displays=list(displays),stdout=stdout.getvalue().strip()))
    plt.close("all")

expr = "quantum:(Y*S*H*T*H*basis(0,2))=([(1-exp(i*pi/4))/2;i*(1+exp(i*pi/4))/2])"
r = subprocess.run([worker,"--json"],input=expr.encode(),capture_output=True,check=True,timeout=30,
                   env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
assert json.loads(r.stdout)["copy_text"]=="1"
assert len(ledger)==18 and sum(row["displays"].count("figure") for row in ledger)==3
print(json.dumps(dict(source_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      versions={p:version(p) for p in ("qiskit","numpy","matplotlib","IPython","pylatexenc","sympy")},
                      calculator_check=expr,cells=ledger,samples=samples),indent=2))

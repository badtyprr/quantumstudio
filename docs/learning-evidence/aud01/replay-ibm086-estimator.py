"""Run the course's hello_qiskit.py against the local Runtime estimator."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

notebook,output=map(Path,sys.argv[1:])
data=notebook.read_bytes()
inventory=json.loads(Path(__file__).with_name("ibm086-inventory.json").read_bytes())
assert hashlib.sha256(data).hexdigest()==inventory["source_sha256"]
blocks=[b for c in json.loads(data)["cells"] for b in re.findall(r"^```python[ \t]*\n(.*?)^```","".join(c["source"]),re.M|re.S) if "hello_qiskit.py" in b]
assert len(blocks)==1
program=ast.parse(blocks[0])
ns={"local_backend":AerSimulator(method="statevector",seed_simulator=71,max_parallel_threads=2)}
for node in program.body:
    if isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=="backend":
        assert "service" in ast.unparse(node.value)
        node.value=ast.copy_location(ast.Name("local_backend",ast.Load()),node.value)
    elif isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=="service":
        assert "QiskitRuntimeService" in ast.unparse(node.value)
        node.value=ast.copy_location(ast.Constant(None),node.value)
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(program,"IBM086-hello-qiskit.py","exec"),ns)
labels=ns["observables_labels"]
assert labels==["IZ","IX","ZI","XI","ZZ","XX"]
state=Statevector.from_instruction(ns["qc"])
exact=np.array([state.expectation_value(op).real for op in ns["observables"]])
assert np.allclose(exact,[0,0,0,0,1,1])
values=np.asarray(ns["pub_result"].data.evs,dtype=float)
assert values.shape==exact.shape and np.max(abs(values-exact))<0.075
output.write_bytes((json.dumps(dict(source_sha256=inventory["source_sha256"],backend="local Aer via Runtime EstimatorV2",
    requested_shots=ns["estimator"].options.default_shots,expectations=dict(zip(labels,values)),reference=dict(zip(labels,exact))),indent=2)+"\n").encode())
print("Verified six Bell observables with the source estimator and a statevector reference.")

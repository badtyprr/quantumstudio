"""Compare all 61 pinned flip-back circuits with their coherent rotation model."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Pauli
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

data = Path(sys.argv[1]).read_bytes()
digest = hashlib.sha256(data).hexdigest()
assert digest == "7b09f95f2f11ea63b11b77acb937e460060ddcd787a50f65c03abc6ba60fe993"
cells = json.loads(data)["cells"]
namespace = {"QuantumCircuit": QuantumCircuit, "Pauli": Pauli}
model = ast.parse("".join(cells[30]["source"]))
# Isolate the lesson's coherent error from backend-dependent calibration.
for node in model.body:
    if isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=="noise_model":
        assert ast.unparse(node.value).startswith("NoiseModel.from_backend(")
        node.value = ast.copy_location(ast.parse("NoiseModel()",mode="eval").body,node.value)
exec(compile(model,"IBM081-cell-30","exec"),namespace)
build = ast.parse("".join(cells[31]["source"]))
# Use Aer density matrices to compare exact expectations at every depth.
end = next(i for i,node in enumerate(build.body) if isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=="estimator")
build.body = build.body[:end]
exec(compile(build,"IBM081-cell-31","exec"),namespace)
circuits = namespace["circuits"]
for circuit, observable in namespace["pubs"]:
    circuit.save_expectation_value(observable,[0],label="z")
simulator = namespace["simulator"]
simulator.set_options(method="density_matrix",max_parallel_threads=4)
result = simulator.run(circuits,shots=1).result()
assert result.success and len(circuits)==61
measured = np.array([result.data(i)["z"] for i in range(len(circuits))])
angle = namespace["theta_error"]
expected = np.cos(2*np.arange(len(circuits))*angle)
error = float(max(abs(measured-expected)))
assert error < 1e-12
report = dict(source_sha256=digest,cells=[30,31],backend="local Aer density matrix",model="coherent X over-rotation only",
              angle_radians=angle,depths=len(circuits),max_absolute_error=error,last_expectation=float(measured[-1]))
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
print("Verified all 61 circuit depths. Maximum expectation error:",error)

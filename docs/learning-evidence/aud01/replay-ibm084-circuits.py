"""Run the pinned GHZ preparation and four-qubit code circuits on local Aer."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
data = args.notebook.read_bytes()
digest = hashlib.sha256(data).hexdigest()
assert digest == "d76bfe7cca292d48e3396c2c1b35c23849ce0e9a22c09b3611f843177811d672"
cells = json.loads(data)["cells"]
namespace = dict(QuantumRegister=QuantumRegister, ClassicalRegister=ClassicalRegister, QuantumCircuit=QuantumCircuit)

# Only circuit construction and the two postselection predicates are required.
for index in (11, 17, 27, 29, 33):
    module = ast.parse("".join(cells[index]["source"]))
    if index in (11, 17, 33):
        module.body = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    else:
        assert ast.unparse(module.body[-1]).startswith(("qc_check.draw(", "qc_logical_phi_plus.draw("))
        module.body.pop()
    exec(compile(module, f"IBM084-cell-{index}", "exec"), namespace)

simulator = AerSimulator(method="stabilizer")
def measure(circuits, shots):
    compiled = transpile(circuits, simulator, optimization_level=0, seed_transpiler=29)
    return simulator.run(compiled, shots=shots, seed_simulator=29).result()

ghz = namespace["ghz_circuit"](10)
counts = measure(ghz, 2048).get_counts()
assert set(counts) == {"0"*10, "1"*10} and sum(counts.values()) == 2048
words = [format(n,"010b") for n in range(1024)]
assert sum(map(namespace["is_all_agree"], words)) == 2
assert sum(map(namespace["has_even_parity"], words)) == 512

bell = Statevector.from_instruction(namespace["qc_logical_phi_plus"])
support = {word for word,p in bell.probabilities_dict().items() if p > 1e-12}
assert support == {"0000","0110","1001","1111"}
assert all(abs(bell.data[int(word,2)]-0.5) < 1e-12 for word in support)

labels = ["no error"]
circuits = [namespace["qc_check"]]
expected = ["00"]
for pauli, syndrome in (("X","01"),("Y","11"),("Z","10")):
    for wire in range(4):
        circuits.append(namespace["build_check_circuit_with_error"](pauli, wire))
        labels.append(f"{pauli}{wire}")
        expected.append(syndrome)
run = measure(circuits,1024)
syndromes = {label:run.get_counts(i) for i,label in enumerate(labels)}
for label,syndrome in zip(labels,expected):
    assert syndromes[label] == {syndrome:1024}
report = dict(source_sha256=digest, backend="local Aer stabilizer simulator", cells=[11,17,27,29,33],
              ghz_counts=counts, logical_bell_support=sorted(support), syndrome_counts=syndromes)
args.output.write_bytes((json.dumps(report, indent=2, sort_keys=True)+"\n").encode())
print("Verified ten-wire GHZ support, all 1,024 postselection inputs and 13 syndrome circuits.")

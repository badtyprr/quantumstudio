"""Execute the original entanglement-in-action code cells and check their results."""
import argparse
from contextlib import redirect_stdout
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO, StringIO
import json
import math
from pathlib import Path
import random

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
raw = args.notebook.read_bytes()
digest = sha256(raw).hexdigest()
assert digest == "4710386ae5132269bef68865323170020d169b002601db142d2bd3160c77ec30"
random.seed(52)
ledger, results = [], {}


def display(item):
    if isinstance(item, Figure):
        image = BytesIO()
        item.savefig(image, format="png")
        assert len(image.getvalue()) > 500
        plt.close(item)
    else:
        assert item.data.strip()
    outputs.append(type(item).__name__)


scope = {"display": display}
for idx, cell in enumerate(json.loads(raw)["cells"]):
    if cell["cell_type"] != "code":
        continue
    source = "".join(cell["source"])
    outputs, stdout = [], StringIO()
    with redirect_stdout(stdout):
        exec(compile(source, f"{args.notebook.name}:cell-{idx}", "exec"), scope)
    ledger.append(dict(cell=idx, source_sha256=sha256(source.encode()).hexdigest(),
                       displays=outputs, stdout=stdout.getvalue().strip()))
    if idx == 13:
        shots = sum(scope["statistics"].values())
        assert shots > 0 and scope["filtered_statistics"] == {"0": shots}
        results["teleportation"] = dict(shots=shots, inverse_gate_result_zero=shots)
    elif idx == 21:
        counts = scope["statistics"]
        assert set(counts) == {scope["c"] + scope["d"]}
        results["fixed_message"] = counts
    elif idx == 25:
        counts = scope["statistics"]
        for bits in counts:
            bob_c, bob_d, alice_c, alice_d = bits.split()
            assert (bob_c, bob_d) == (alice_c, alice_d)
        results["random_messages"] = counts
    elif idx in (35, 39):
        assert scope["NUM_GAMES"] == 1000 and 0 <= scope["TOTAL_SCORE"] <= 1000
        results["quantum_wins" if idx == 35 else "classical_wins"] = scope["TOTAL_SCORE"]

assert len(ledger) == 19
classical_wins = 0
probabilities = []
for x in (0, 1):
    for y in (0, 1):
        a, b = scope["classical_strategy"](x, y)
        classical_wins += (a ^ b) == (x & y)
        original = scope["chsh_circuit"](x, y)
        # The two local measurements commute with the other wire's rotation.
        # Removing them gives the joint distribution immediately before readout.
        unitary = QuantumCircuit(2)
        for instruction in original.data:
            if instruction.operation.name not in ("measure", "barrier"):
                wires = [original.find_bit(q).index for q in instruction.qubits]
                unitary.append(instruction.operation, wires)
        distribution = Statevector.from_instruction(unitary).probabilities_dict()
        win = sum(p for bits,p in distribution.items() if (int(bits[0]) ^ int(bits[1])) == (x & y))
        assert abs(win-(2+math.sqrt(2))/4) < 1e-13
        probabilities.append(float(win))
assert classical_wins == 3
results.update(classical_exact="3/4", quantum_per_input=probabilities)
report = dict(notebook_sha256=digest, qiskit=version("qiskit"), aer=version("qiskit-aer"),
              python_random_seed=52, code_cells=ledger, results=results)
args.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf8")
print("Verified all 19 original cells, both communication protocols and the four CHSH input distributions.")

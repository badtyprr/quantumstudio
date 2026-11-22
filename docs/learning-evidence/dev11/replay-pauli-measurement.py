"""Check IBM-058 Pauli measurements or IBM-067 Shor cat-state error detection.

Arguments are the compiler Python, qasm-import.py, saved-circuit adapter,
quantum-worker executable, and a new JSON report path.
"""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np


H = np.array([[1, 1], [1, -1]]) / math.sqrt(2)
S = np.diag([1, 1j])
I = np.eye(2)
PAULI = dict(I=I, X=np.array([[0, 1], [1, 0]]), Y=np.array([[0, -1j], [1j, 0]]), Z=np.diag([1, -1]))
PREP = {"0": (), "1": ("x",), "+": ("h",), "i": ("h", "s")}
READ = {"Z": (), "X": ("h",), "Y": ("sdg", "h")}


def tensor(operators):
    product = 1
    for op in reversed(operators):
        product = np.kron(product, op)
    return product


def reference(paulis, initial, bases):
    states = {"0": [1, 0], "1": [0, 1], "+": H[:, 0], "i": S @ H[:, 0]}
    rotations = {"Z": I, "X": H, "Y": H @ S.conj().T}
    psi = tensor([states[v] for v in initial])
    flipped = tensor([PAULI[v] for v in paulis]) @ psi
    read = tensor([rotations[v] for v in bases])
    probabilities = {}
    for syndrome in (0, 1):
        projected = read @ ((psi + (-1) ** syndrome * flipped) / 2)
        for i, amplitude in enumerate(projected):
            probability = float(abs(amplitude) ** 2)
            if probability > 1e-12:
                probabilities[str(syndrome) + format(i, f"0{len(initial)}b")] = probability
    return probabilities


def circuit(paulis, initial, bases, simplified):
    ancilla = len(initial)
    lines = ['OPENQASM 3;', 'include "stdgates.inc";', f'qubit[{ancilla + 1}] q;', f'bit[{ancilla + 1}] b;']
    for wire, state in enumerate(initial):
        lines.extend(f"{gate} q[{wire}];" for gate in PREP[state])
    if simplified:
        assert paulis == "ZZ"
        lines.extend(f"cx q[{wire}], q[{ancilla}];" for wire in (0, 1))
    else:
        lines.append(f"h q[{ancilla}];")
        for wire, op in enumerate(paulis):
            if op != "I":
                lines.append(f"c{op.lower()} q[{ancilla}], q[{wire}];")
        lines.append(f"h q[{ancilla}];")
    lines.append(f"b[{ancilla}] = measure q[{ancilla}];")
    for wire, basis in enumerate(bases):
        lines.extend(f"{gate} q[{wire}];" for gate in READ[basis])
        lines.append(f"b[{wire}] = measure q[{wire}];")
    return ("\n".join(lines) + "\n").encode()


def execute(command, payload, env=None):
    return subprocess.run(command, input=payload, capture_output=True, check=True, timeout=60, env=env).stdout


def shor_circuit(paulis, initial, bases, fault, target):
    lines = ['OPENQASM 3;', 'include "stdgates.inc";', 'qubit[6] q;', 'bit[7] b;']
    for wire, state in enumerate(initial):
        lines.extend(f"{gate} q[{wire}];" for gate in PREP[state])
    lines.extend(["h q[3];", "cx q[3],q[4];", "cx q[3],q[5];"])
    if fault:
        lines.append(f"{fault.lower()} q[{3 + target}];")
    # The diagram couples the bottom pair first. Each cat wire controls one data wire.
    for wire in (2, 1, 0):
        lines.append(f"c{paulis[wire].lower()} q[{3 + wire}],q[{wire}];")
    for wire in (3, 4, 5):
        lines.extend([f"h q[{wire}];", f"b[{wire}] = measure q[{wire}];"])
    lines.append("b[6] = b[3] ^ b[4] ^ b[5];")
    for wire, basis in enumerate(bases):
        lines.extend(f"{gate} q[{wire}];" for gate in READ[basis])
        lines.append(f"b[{wire}] = measure q[{wire}];")
    return ("\n".join(lines) + "\n").encode()


def shor_reference(paulis, initial, bases, fault, target):
    # Four equiprobable cat words encode each parity. A Z component flips
    # that parity. An X component propagates the single target Pauli.
    joint = reference(paulis, initial, bases)
    phase_fault = fault in ("Z", "Y")
    data_flip = fault in ("X", "Y") and paulis[target] != bases[target]
    probabilities = {}
    for word in range(8):
        parity = word.bit_count() % 2
        for bits, probability in joint.items():
            if int(bits[0]) == (parity ^ phase_fault):
                data = int(bits[1:], 2) ^ ((1 << target) if data_flip else 0)
                probabilities[f"{parity}{word:03b}{data:03b}"] = probability / 4
    return probabilities


def shor_cases():
    inputs = [("ZZZ", f"{i:03b}", "ZZZ", None, 0) for i in range(8)]
    inputs.extend([("XYZ", "+i1", "XYZ", None, 0), ("XXX", "000", "XXX", None, 0)])
    inputs.extend(("XXX", "000", "ZZZ", fault, wire)
                  for wire in range(3) for fault in ("X", "Y", "Z"))
    inputs.append(("XXX", "000", "ZZZ", None, 0))
    inputs.extend(("XXX", "000", "XXX", fault, wire)
                  for wire in range(3) for fault in ("Y", "Z"))
    for paulis, initial, bases, fault, wire in inputs:
        details = dict(pauli=paulis, preparation=initial, readout=bases,
                       cat_fault=fault, fault_wire=wire if fault else None)
        yield (details, shor_circuit(paulis, initial, bases, fault, wire),
               shor_reference(paulis, initial, bases, fault, wire))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python", "compiler", "adapter", "worker", "report"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--shor", action="store_true", help="Run the six-wire IBM-067 cat-state circuit")
    a = parser.parse_args()
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(a.worker.resolve().parent / "data"))
    cases = [(p, state, p, False) for p, state in [("X", "+"), ("Y", "i"), ("Z", "1")]]
    cases += [("XYZ", "+i1", "XYZ", False), ("YIX", "000", "XYZ", False)]
    for simplified in (False, True):
        cases.extend(("ZZ", state, "ZZ", simplified) for state in ("00", "01", "10", "11"))
        cases.extend(("ZZ", "++", basis, simplified) for basis in ("ZZ", "XX", "YY"))
    measurements = ((dict(pauli=p, preparation=s, readout=b, simplified=simple),
                     circuit(p, s, b, simple), reference(p, s, b)) for p, s, b, simple in cases)
    rows = []
    for details, program, expected in (shor_cases() if a.shor else measurements):
        model = execute([a.python, "-B", a.compiler, "--classical"], program)
        payloads = json.loads(execute([a.adapter], model).decode("utf-8-sig"))
        results = {}
        for mode, flag in [("exact", "--exact-circuit"), ("sampled", "--sample")]:
            raw = json.loads(execute([a.worker, flag], base64.b64decode(payloads[mode]), env))
            if mode == "exact":
                actual = {k: float(v) for k, v in raw["probabilities"].items()}
            else:
                assert sum(raw["counts"].values()) == 10000
                actual = {k: v / 10000 for k, v in raw["counts"].items()}
            assert set(actual) == set(expected), (mode, actual, expected)
            residual = max(abs(actual[k] - expected[k]) for k in expected)
            assert residual <= (1e-10 if mode == "exact" else 0.03), (mode, actual, expected)
            results[mode] = residual
        rows.append(dict(**details, expected=expected, max_probability_error=results))
    with a.report.open("x", encoding="utf-8") as output:
        json.dump(rows, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()

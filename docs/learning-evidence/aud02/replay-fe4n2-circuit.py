"""Replay the publisher's Fe4N2 circuit with pytket, Qiskit and QuantumStudio."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

import numpy as np
from pytket.circuit import Circuit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import StatePreparation


class PublisherPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.circuits = []
        self.frames = []
        self.in_circuit = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "iframe" and "srcdoc" in attrs:
            self.frames.append(attrs["srcdoc"])
        if tag == "div" and attrs.get("id") == "circuit-json-to-display":
            self.in_circuit = True

    def handle_endtag(self, tag):
        if tag == "div":
            self.in_circuit = False

    def handle_data(self, text):
        if self.in_circuit:
            self.circuits.append(json.loads(text))


def sample(worker, gates):
    shots = 100000
    request = ["QSAMPLE1", "6", str(shots), "12345", "6", *map(str, range(6)), str(len(gates))]
    data = bytearray(("\n".join(request) + "\n").encode())
    for wires, expression in gates:
        encoded = expression.encode()
        data.extend(("\n".join(map(str, [len(wires), *wires, len(encoded)])) + "\n").encode())
        data.extend(encoded)
    p = subprocess.run([str(worker), "--sample"], input=data, capture_output=True, timeout=180)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace"))
    counts = json.loads(p.stdout)["counts"]
    assert sum(counts.values()) == shots
    return counts


def replay(page, worker):
    record = json.loads(Path(__file__).with_name("fe4n2-circuit-replay.json").read_bytes())
    raw = page.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record["html_sha256"], "Unexpected tutorial revision"
    parser = PublisherPage()
    parser.feed(raw.decode("utf-8"))
    for frame in parser.frames.copy():
        parser.feed(frame)
    # The publisher may render identical copies for desktop and mobile views.
    unique = {json.dumps(c, sort_keys=True, separators=(",", ":")) for c in parser.circuits}
    assert len(unique) == 1
    serialized = unique.pop()
    assert hashlib.sha256(serialized.encode()).hexdigest() == record["circuit_sha256"]
    source = Circuit.from_dict(json.loads(serialized))
    published = record["published_parameters"]
    assert {str(s) for s in source.free_symbols()} == set(published)
    source.symbol_substitution({s: published[str(s)] for s in source.free_symbols()})

    notation = {"S": "Rz(pi/2)", "Sdg": "Rz(-pi/2)", "V": "Rx(pi/2)", "Vdg": "Rx(-pi/2)",
                "H": "H", "X": "X", "CX": "CX"}
    gates = []
    for cmd in source.get_commands():
        name = cmd.op.type.name
        expression = f"Rz(({float(cmd.op.params[0]):.17f})*pi)" if name == "Rz" else notation[name]
        gates.append(([q.index[0] for q in cmd.qubits], expression))
    assert len(gates) == 311 and sum(len(w) == 2 for w, _ in gates) == 59 and source.n_qubits == 6

    errors = {}
    for check in record["sample_checks"]:
        reference = source.copy()
        steps = gates.copy()
        basis = check["basis"]
        for wire in range(6):
            if basis == "Y":
                reference.Sdg(wire)
                steps.append(([wire], "Rz(-pi/2)"))
            if basis != "Z":
                reference.H(wire)
                steps.append(([wire], "H"))
        counts = sample(worker, steps)
        expected = np.abs(reference.get_statevector()) ** 2
        errors[basis] = max(abs(counts.get(f"{i:06b}", 0) / check["shots"] - p)
                            for i, p in enumerate(expected))
        assert errors[basis] <= check["limit"]

    ref = QuantumCircuit(6)
    ref.append(StatePreparation(source.get_statevector()).inverse(), range(6))
    inverse = []
    decomposed = transpile(ref, basis_gates=["u", "cx"], optimization_level=0, seed_transpiler=7)
    for inst in decomposed.data:
        # Qiskit indexes from the least significant bit. Native wire zero is leftmost.
        wires = [5 - decomposed.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "cx":
            inverse.append((wires, "CX"))
        else:
            assert inst.operation.name == "u"
            theta, phi, lam = map(float, inst.operation.params)
            inverse.extend((wires, f"{op}({a:.17f})")
                           for op, a in [("Rz", lam), ("Ry", theta), ("Rz", phi)] if a)
    assert sample(worker, gates + inverse) == {"000000": 100000}
    assert sample(worker, gates + [([0], "X")] + inverse).get("000000", 0) == 0
    print(json.dumps({"max_probability_errors": errors, "reference_projection": 100000, "control": 0}))


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("page", type=Path)
    args.add_argument("worker", type=Path)
    options = args.parse_args()
    replay(options.page, options.worker.resolve())

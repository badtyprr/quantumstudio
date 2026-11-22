"""Replay IBM-056 on nine code wires, eight syndrome wires, a reference and a channel environment."""
import argparse
import json
import math
from pathlib import Path
import runpy
import subprocess

import numpy as np


DIAGRAM = runpy.run_path(str(Path(__file__).with_name("diagram-audit.py")))
PAULIS = {"I": np.eye(2), "X": np.array([[0, 1], [1, 0]]),
          "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1, -1])}
PAIRS = [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)]
BLOCKS = [range(6), range(3, 9)]


def channel(name, site):
    if name in ("unitary", "flagged-phase"):
        angle = .73
        c, s = math.cos(angle/2), math.sin(angle/2)
        unitary = np.array([[c, -s], [1j*s, 1j*c]])
        gates = [("RY", site, angle), ("S", site)]
        if name == "unitary":
            return gates, [unitary]
        # Both environment components contribute to every syndrome. This checks
        # their relative phase as well as the surviving logical-reference state.
        gates.extend([("RY", 18, 1.1), ("H", site), ("CNOT", 18, site), ("H", site)])
        return gates, [math.cos(.55)*unitary, math.sin(.55)*PAULIS["Z"] @ unitary]
    # Dilation of amplitude damping with gamma=1/4, environment initially zero.
    half = math.pi / 6
    gates = [("RY", 18, half), ("CNOT", site, 18), ("RY", 18, -half),
             ("CNOT", site, 18), ("CNOT", 18, site)]
    return gates, [np.diag([1, math.sqrt(.75)]), np.array([[0, .5], [0, 0]])]


def extraction():
    gates = []
    for i, pair in enumerate(PAIRS):
        gates.extend(("CNOT", data, 9+i) for data in pair)
    for i, block in enumerate(BLOCKS):
        anc = 15+i
        gates.append(("H", anc))
        gates.extend(("CNOT", anc, data) for data in block)
        gates.append(("H", anc))
    return gates


def syndrome(label, site):
    # A Pauli anticommutes with a check precisely when its opposite component overlaps.
    bits = [int(label in ("X", "Y") and site in pair) for pair in PAIRS]
    bits += [int(label in ("Z", "Y") and site in block) for block in BLOCKS]
    return int("".join(map(str, bits)), 2)


def recovery():
    gates = []
    for block in range(3):
        shift = 6 - 2*block
        for offset, pattern in enumerate((2, 3, 1)):
            gates.append(("F", 3*block+offset, 3 << shift, pattern << shift, "X"))
    for block, pattern in enumerate((2, 3, 1)):
        gates.append(("F", 3*block, 3, pattern, "Z"))
    return gates


def reference(label, site, operators, record, corrected=False):
    coefficients = [np.trace(PAULIS[label] @ op)/2 for op in operators]
    result = {}
    mask = 1 << (8-site)
    for logical in (0, 1):
        for triple in range(8):
            word = int("".join(bit*3 for bit in f"{triple:03b}"), 2)
            encoded = (-1)**(logical*triple.bit_count()) / 4  # encoded Bell pair
            for env, weight in enumerate(coefficients):
                output = word
                phase = 1
                if not corrected:
                    if label in ("Z", "Y") and word & mask:
                        phase = -1
                    if label == "Y":
                        phase *= 1j
                    if label in ("X", "Y"):
                        output ^= mask
                index = (output << 10) | (record << 2) | (logical << 1) | env
                result[index] = encoded * weight * phase
    return result


def packet(gates):
    return f"19 {len(gates)}\n" + "\n".join(" ".join(map(str, g)) for g in gates) + "\n"


def residual(out, expected, allow_phase=False):
    assert abs(out["norm"] - 1) < 1e-10
    actual = {i: complex(x, y) for i, x, y in out["amplitudes"]}
    phase = 1
    if allow_phase:
        pivot = max(expected, key=lambda k: abs(expected[k]))
        phase = actual[pivot] / expected[pivot]
        phase /= abs(phase)
    return max(abs(actual.get(k, 0) - phase*expected.get(k, 0)) for k in actual.keys() | expected.keys())


def check(adapter, name, site):
    noise, operators = channel(name, site)
    gates = [("H", 17), ("CNOT", 17, 0)] + DIAGRAM["SHOR"] + noise + extraction()
    packets = [packet(gates)]
    sectors = {}
    for label in PAULIS:
        record = syndrome(label, site)
        branch = reference(label, site, operators, record)
        probability = float(sum(abs(x)**2 for x in branch.values()))
        measures = [("M", 9+i, 7-i, .999999 if record & (1 << (7-i)) else .000001) for i in range(8)]
        assert probability > 0 and record not in sectors
        sectors[record] = (label, probability, branch)
        packets.extend([packet(gates+measures), packet(gates+measures+recovery())])
    run = subprocess.run([adapter], input="".join(packets), text=True, capture_output=True, check=True, timeout=180)
    states = [json.loads(line) for line in run.stdout.splitlines()]
    assert len(states) == 9
    error = residual(states[0], {k: v for _, _, branch in sectors.values() for k, v in branch.items()})
    for i, (record, (label, probability, branch)) in enumerate(sectors.items()):
        measured, recovered = states[1+2*i:3+2*i]
        assert measured["record"] == recovered["record"] == record
        scale = math.sqrt(probability)
        error = max(error, residual(measured, {k: v/scale for k, v in branch.items()}))
        restored = reference(label, site, operators, record, corrected=True)
        error = max(error, residual(recovered, {k: v/scale for k, v in restored.items()}, allow_phase=True))
    assert error < 1e-10, (name, site, error)
    return dict(channel=name, physical_site=site, max_amplitude_error=error,
                sectors={label: [f"{record:08b}", probability] for record, (label, probability, _) in sectors.items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    rows = [check(args.adapter, channel_name, site) for channel_name in ("unitary", "amplitude-damping", "flagged-phase") for site in range(9)]
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
        f.write("\n")

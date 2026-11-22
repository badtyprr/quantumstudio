"""Check the two IBM-067 Steane readouts with the product state-vector adapter.

Pass the compiled diagram-native executable and a new report path.
"""
import argparse
import json
import runpy
import subprocess
from pathlib import Path


diagram = runpy.run_path(str(Path(__file__).with_name("diagram-audit.py")))
ENCODE = diagram["STEANE"]
DUAL = [int(word[::-1], 2) for word in ("0011110", "0101101", "1001011")]


def syndrome(word):
    return tuple((word & check).bit_count() % 2 for check in DUAL)


def expected_data(state, fault, mask):
    physical = {}
    for word, amplitude in enumerate(diagram["logical_state"]("steane", state)):
        if amplitude:
            phase = -1 if fault in ("Z", "Y") and word & mask else 1
            new_word = word ^ mask if fault in ("X", "Y") else word
            # The circuit realizes simultaneous bit and phase faults as Z then X.
            physical[new_word] = phase * amplitude
    return physical


def gates(kind, state, fault, wire):
    ops = list(diagram["prepare"](state)) + ENCODE
    if fault in ("Z", "Y"):
        ops.append(("Z", wire))
    if fault in ("X", "Y"):
        ops.append(("X", wire))
    if kind == "X":
        ops.append(("H", 7))
    ops.extend((op[0], *(i + 7 for i in op[1:])) for op in ENCODE)
    for i in range(7):
        pair = (i, 7 + i) if kind == "X" else (7 + i, i)
        ops.append(("CNOT", *pair))
    if kind == "Z":
        ops.extend(("H", 7 + i) for i in range(7))
    return ops


def packet(ops):
    return "14 " + str(len(ops)) + "\n" + "\n".join(" ".join(map(str, op)) for op in ops) + "\n"


def residual(result, expected):
    actual = {i: complex(re, im) for i, re, im in result["amplitudes"]}
    assert abs(result["norm"] - 1) < 1e-10
    return max(abs(actual.get(i, 0) - expected.get(i, 0)) for i in actual.keys() | expected.keys())


def check(adapter, kind, state, fault, wire):
    ops = gates(kind, state, fault, wire)
    mask = 0 if wire is None else 1 << (6 - wire)
    expected_syndrome = syndrome(mask if fault in (kind, "Y") else 0)
    words = [word for word in range(128) if syndrome(word) == expected_syndrome]
    assert len(words) == 16
    data = expected_data(state, fault, mask)
    requests = [packet(ops)]
    for word in words:
        measures = [("M", 7 + i, 6 - i, 0.999999 if word & (1 << (6-i)) else 0.000001)
                    for i in range(7)]
        requests.append(packet(ops + measures))
    run = subprocess.run([adapter], input="".join(requests), text=True, capture_output=True, check=True, timeout=120)
    outcomes = [json.loads(line) for line in run.stdout.splitlines()]
    assert len(outcomes) == 17
    before = {(d << 7) | word: amplitude / 4 for d, amplitude in data.items() for word in words}
    error = residual(outcomes[0], before)
    for word, outcome in zip(words, outcomes[1:]):
        assert outcome["record"] == word
        error = max(error, residual(outcome, {(d << 7) | word: a for d, a in data.items()}))
    assert error < 1e-10, (kind, state, fault, wire, error)
    return dict(detect=kind, logical_input=state, fault=fault, wire=wire,
                expected_syndrome=expected_syndrome, measured_branches=len(words), max_amplitude_error=error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cases = [(state, None, None) for state in ("0", "1", "+i")]
    cases.extend(("+i", fault, wire) for fault in ("X", "Y", "Z") for wire in range(7))
    rows = [check(args.adapter, kind, *case) for kind in ("X", "Z") for case in cases]
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(rows, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()

"""Replay the classical control wires in both IBM-066 teleportation diagrams."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess


PREP = {"0": [], "1": ["x"], "+": ["h"], "-": ["x", "h"],
        "+i": ["h", "s"], "-i": ["x", "h", "s"]}


def circuit(state, wiring, logical):
    entangled = state == "Bell"
    width = 4 if entangled else 3
    lines = ['OPENQASM 3;', 'include "stdgates.inc";', f'qubit[{width}] q;', f'bit[{width}] b;']
    if entangled:
        lines.extend(["h q[0];", "cx q[0],q[3];"])
    else:
        lines.extend(f"{gate} q[0];" for gate in PREP[state])
    lines.extend(["h q[2];", "cx q[2],q[1];", "cx q[0],q[1];", "h q[0];"])
    # In the ideal logical comparison, EC acts as identity on the code space.
    for wire in ((0, 1) if logical else (1, 0)):
        lines.append(f"b[{wire}] = measure q[{wire}];")
    xbit, zbit = (0, 1) if wiring == "diagram" else (1, 0)
    lines.extend([f"if (b[{xbit}]) {{ x q[2]; }}", f"if (b[{zbit}]) {{ z q[2]; }}"])
    if entangled:
        lines.extend(["cx q[2],q[3];", "h q[2];", "b[3] = measure q[3];"])
    else:
        for gate in reversed(PREP[state]):
            lines.append(f"{'sdg' if gate == 's' else gate} q[2];")
    lines.append("b[2] = measure q[2];")
    return ("\n".join(lines) + "\n").encode()


def expected_bits(state, wiring):
    # Before correction the bottom wire holds X^middle Z^top |psi>.
    # Swapping the two controls leaves Y (up to phase) on unequal outcomes.
    expected = {}
    for middle in (0, 1):
        for top in (0, 1):
            residual_y = wiring == "diagram" and middle != top
            if state == "Bell":
                readout = "11" if residual_y else "00"
            else:
                readout = str(int(residual_y and state not in ("+i", "-i")))
            expected[readout + str(middle) + str(top)] = 0.25
    return expected


def run(command, payload, env=None):
    return subprocess.run(command, input=payload, capture_output=True, check=True, timeout=60, env=env).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python", "compiler", "adapter", "worker", "output"):
        parser.add_argument(name, type=Path)
    a = parser.parse_args()
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(a.worker.resolve().parent / "data"))
    records = []
    for logical in (False, True):
        for wiring in ("diagram", "teleportation-control"):
            for state in (*PREP, "Bell"):
                document = run([a.python, "-B", a.compiler, "--classical"], circuit(state, wiring, logical))
                inputs = json.loads(run([a.adapter], document).decode("utf-8-sig"))
                expected = expected_bits(state, wiring)
                checks = {}
                for mode, flag in [("exact", "--exact-circuit"), ("sampled", "--sample")]:
                    result = json.loads(run([a.worker, flag], base64.b64decode(inputs[mode]), env))
                    if mode == "exact":
                        actual = {key: float(value) for key, value in result["probabilities"].items()}
                    else:
                        assert sum(result["counts"].values()) == 10000
                        actual = {key: value / 10000 for key, value in result["counts"].items()}
                    assert set(actual) == set(expected), (state, wiring, actual)
                    error = max(abs(actual[k] - expected[k]) for k in expected)
                    assert error <= (1e-10 if mode == "exact" else .03)
                    checks[mode] = error
                records.append(dict(ideal_logical=logical, wiring=wiring, input=state, joint=expected, errors=checks))
    with a.output.open("x", encoding="utf-8") as stream:
        json.dump(records, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()

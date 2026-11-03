"""DEV-11c packaged-worker circuit witnesses; no new product operation.

The full-amplitude native regression is quantum-steane-transversal-test.cc.
This supplementary run tests the actual packaged worker's existing numerical
circuit protocol. Sample frequencies are not exact amplitude certification.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


DUAL = (0, 30, 45, 51, 75, 85, 102, 120)


def encoder(offset):
    gates = [((offset + 6, offset + q), "CX") for q in (4, 5)]
    gates += [((offset + q,), "H") for q in range(3)]
    gates += [((offset + a, offset + b), "CX") for a, b in
              ((0, 3), (0, 5), (0, 6), (1, 3), (1, 4), (1, 6),
               (2, 3), (2, 4), (2, 5))]
    return gates


def request(gates, shots):
    fields = ["QSAMPLE1", "14", str(shots), "674062", "14",
              *map(str, range(14)), str(len(gates))]
    payload = ("\n".join(fields) + "\n").encode()
    for wires, expression in gates:
        value = expression.encode()
        payload += ("\n".join(map(str, [len(wires), *wires, len(value)])) + "\n").encode() + value
    return payload


def qasm(gates):
    lines = ['OPENQASM 3.0;', 'include "stdgates.inc";', 'qubit[14] q;', 'bit[14] b;']
    for wires, gate in gates:
        names = {"H": "h", "X": "x", "S": "s", "Sdg": "sdg", "CX": "cx"}
        lines.append(names[gate] + " " + ", ".join(f"q[{q}]" for q in wires) + ";")
    lines += [f"b[{q}] = measure q[{q}];" for q in range(14)]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    args = parser.parse_args()
    args.worker = args.worker.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(Path(__file__).with_name("source-manifest.json").read_text())
    sources = []
    for item in manifest:
        if item["id"] in ("IBM-062", "IBM-067"):
            path = args.sources / (item["id"] + ".ipynb")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["notebook"]["sha256"]
            sources.append(item)
    assert len(sources) == 2
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.parent / "data"))
    encoding = encoder(0) + encoder(7)
    transversal = [((q, q + 7), "CX") for q in range(7)]
    fixtures = []
    for input_column in range(4):
        a, b = input_column >> 1, input_column & 1
        preparation = ([((6,), "X")] if a else []) + ([((13,), "X")] if b else [])
        support = {f"{((u ^ (127 * a)) << 7) | (v ^ (127 * (a ^ b))):014b}"
                   for u in DUAL for v in DUAL}
        fixtures.append((f"column-{input_column}", preparation + encoding + transversal, support))
    # An entangling logical input preparation gives four nonzero complex
    # coefficients (1,i,i,1)/2. Decode, undo the independent logical CNOT, and
    # unprepare: every physical bit must return to zero. A phase error cannot
    # be accepted merely because its computational support is unchanged.
    preparation = [((6,), "H"), ((13,), "H"), ((13,), "S"), ((6, 13), "CX")]
    unprepare = [((6, 13), "CX"), ((13,), "Sdg"), ((13,), "H"), ((6,), "H")]
    echo = preparation + encoding + transversal + list(reversed(encoding)) + [((6, 13), "CX")] + unprepare
    fixtures.append(("coherent-echo", echo, {"0" * 14}))
    results = []
    report = dict(mode="fresh packaged numerical sampling", utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  worker=str(args.worker), worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  sources=sources, shots=16384, seed=674062, results=results)
    for name, gates, support in fixtures:
        payload = request(gates, 16384)
        (args.output / (name + ".request")).write_bytes(payload)
        (args.output / (name + ".qasm")).write_text(qasm(gates), encoding="utf-8")
        run = subprocess.run([str(args.worker), "--sample"], input=payload, env=env, capture_output=True, timeout=90)
        (args.output / (name + ".stdout")).write_bytes(run.stdout)
        (args.output / (name + ".stderr")).write_bytes(run.stderr)
        result = dict(name=name, returncode=run.returncode, request_sha256=hashlib.sha256(payload).hexdigest(),
                      gates=gates, expected_support=sorted(support))
        results.append(result)
        if run.returncode == 0:
            actual = json.loads(run.stdout)
            result["actual"] = actual
            result["passed"] = set(actual["counts"]) == support and sum(actual["counts"].values()) == 16384
            # Conservative fixed-seed frequency check for the uniform 64-word
            # columns, supplementary to the deterministic native amplitude test.
            result["passed"] &= all(abs(count - 16384 / len(support)) < 128 for count in actual["counts"].values())
        else:
            result["passed"] = False
        (args.output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        assert result["passed"], name
    assert hashlib.sha256(args.worker.read_bytes()).hexdigest() == report["worker_sha256"]
    print("PASS: 4 encoded columns and coherent echo on packaged numerical worker")


if __name__ == "__main__":
    main()

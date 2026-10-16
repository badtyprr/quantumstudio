"""Test the numerical sampling process protocol, including ordered measurement bits."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else "quantum-worker" + (".exe" if os.name == "nt" else "")).resolve()
checks = 0

def request(qubits=2, shots=10000, seed=7, wires=(0, 1), gates=()):
    fields = ["QSAMPLE1", str(qubits), str(shots), str(seed), str(len(wires))]
    fields += list(map(str, wires)) + [str(len(gates))]
    value = ("\n".join(fields) + "\n").encode()
    for targets, expression in gates:
        encoded = expression.encode("utf-8")
        value += ("\n".join(map(str, [len(targets), *targets, len(encoded)])) + "\n").encode() + encoded
    return value

def run(value, success=True, flags=("--sample",)):
    global checks
    process = subprocess.run([str(worker), *flags], input=value, capture_output=True, timeout=30)
    assert (process.returncode == 0) == success, (value[:150], process.returncode, process.stderr)
    checks += 1
    if not success:
        assert process.stdout == b"" and process.stderr
        return
    result = json.loads(process.stdout)
    assert set(result) == {"qubits", "shots", "seed", "wires", "counts"}
    assert sum(result["counts"].values()) == result["shots"]
    assert all(len(bits) == len(result["wires"]) and set(bits) <= {"0", "1"} for bits in result["counts"])
    return result

assert run(request())["counts"] == {"00": 10000}
bell_request = request(gates=[((0,), "H"), ((0, 1), "CX")])
bell = run(bell_request)
assert set(bell["counts"]) == {"00", "11"}
assert abs(bell["counts"]["00"] - 5000) < 250
assert run(bell_request) == bell
assert run(request(seed=8, gates=[((0,), "H"), ((0, 1), "CX")]))["counts"] != bell["counts"]
for wires, expected in [((0, 1, 2), "100"), ((2, 0), "01"), ((1,), "0"), ((), "")]:
    assert run(request(qubits=3, wires=wires, gates=[((0,), "X")]))["counts"] == {expected: 10000}
assert run(request(gates=[((1,), "X"), ((1, 0), "CX")]))["counts"] == {"11": 10000}
assert run(request(gates=[((0,), "H"), ((0,), "Z"), ((0,), "H")]))["counts"] == {"10": 10000}
assert run(request(gates=[((0,), "Rx(pi)"), ((1,), "[1,0;0,i]")]))["counts"] == {"10": 10000}
assert run(request(qubits=0, wires=(), shots=12))["counts"] == {"": 12}
assert run(request(shots=0))["counts"] == {}
assert run(request(seed=2**64-1))["seed"] == str(2**64-1)
assert run(request(qubits=11, wires=(10,0), gates=[((10,), "X")]))["counts"] == {"10": 10000}
assert run(request(qubits=3, wires=(2,0,1), gates=[((0,), "X"), ((1,), "X"), ((0,1,2), "CCX")]))["counts"] == {"111": 10000}
assert run(request(gates=[((0,1), "H⊗H"), ((0,1), "H⊗H")]))["counts"] == {"00": 10000}
assert run(request(gates=[((0,), "[0,\r\n1;1,0]")]))["counts"] == {"10": 10000}
assert run(request(qubits=0, wires=(), shots=1000000))["counts"] == {"": 1000000}
# Every strict prefix must fail, including truncation inside raw expression bytes.
for cut in range(len(bell_request)):
    run(bell_request[:cut], success=False)
for bad in [
    b"", b"QSAMPLE2\n", request() + b"x", request()[:-1],
    request(qubits=26), request(qubits=-1), request(shots=1000001),
    request(seed=2**64), request(seed=-1), request(wires=(0,0)), request(wires=(2,)),
    request(qubits=0, wires=(0,)), request(gates=[((), "1")]),
    request(gates=[((0,0), "CX")]), request(gates=[((2,), "H")]),
    request(gates=[((0,1,0,1), "H")]),
    request(gates=[((0,), "1")]), request(gates=[((0,), "[1;0]")]),
    request(gates=[((0,), "[2,0;0,1]")]), request(gates=[((0,), "[a,0;0,1]")]),
    request(gates=[((0,), "[infinity,0;0,1]")]), request(gates=[((0,), "[interval(0,1),0;0,1]")]),
    request(gates=[((0,), "Rx(theta)")]), request(gates=[((0,), "")]),
    request(gates=[((0,), "H\x00")]), request(gates=[((0,), "H"*4097)]),
    b"QSAMPLE1\n" + b"0"*21 + b"\n", b"x"*1100001,
    request(gates=[((0,), "H")])[:-1],
]:
    run(bad, success=False)
run(request(), success=False, flags=("--sample", "--json"))
run(request(), success=False, flags=("--sample", "--sample"))
print(f"PASS: {checks} numerical sampling process checks.")

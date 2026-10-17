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
    assert set(result) == ({"qubits", "shots", "seed", "wires", "counts", "classical_bits"} if value.startswith(b"QSAMPLE2\n") else {"qubits", "shots", "seed", "wires", "counts"})
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


# QSAMPLE2: explicit classical memory and ordered trajectory operations.
def trajectory(qubits=2, classical=2, bits=(0,1), steps=(), shots=1000, seed=7):
    fields = ["QSAMPLE2", str(qubits), str(shots), str(seed), str(classical), str(len(bits)), *map(str,bits), str(len(steps))]
    data = ("\n".join(fields)+"\n").encode()
    for step in steps:
        kind, *args = step
        data += (str(kind)+"\n").encode()
        if kind in (0,3,4,5):
            if kind == 3:
                mask, value, targets, expression = args
                data += f"{mask}\n{value}\n".encode()
            else:
                targets, expression = args
            encoded = expression.encode()
            data += ("\n".join(map(str,[len(targets),*targets,len(encoded)]))+"\n").encode()+encoded
        else:
            data += ("\n".join(map(str,args))+"\n").encode()
    return data

saved = [(0,(0,),"X"),(1,0,0),(2,0),(3,1,1,(1,),"X"),(1,1,1)]
assert run(trajectory(steps=saved))["counts"] == {"11":1000}
assert run(trajectory(steps=saved[:-1],bits=(1,0)))["counts"] == {"01":1000}
assert run(trajectory(steps=[(0,(0,),"X"),(1,0,0),(2,0),(1,0,0)]))["counts"] == {"00":1000}
# Teleport a nontrivial complex state; inverse preparation on Bob returns zero.
teleport = [(0,(0,),"Ry(pi/3)"),(0,(0,),"Rz(pi/5)"),(0,(1,),"H"),(0,(1,2),"CX"),
            (0,(0,1),"CX"),(0,(0,),"H"),(1,0,0),(1,1,1),
            (3,2,2,(2,),"X"),(3,1,1,(2,),"Z"),
            (0,(2,),"Rz(-pi/5)"),(0,(2,),"Ry(-pi/3)"),(1,2,2)]
t = trajectory(qubits=3,classical=3,bits=(0,1,2),steps=teleport,shots=2000)
r = run(t)
assert set(r["counts"]) == {"000","010","100","110"}
assert all(abs(n-500)<100 for n in r["counts"].values())
assert run(t) == r
assert run(trajectory(classical=64,bits=(63,),steps=[(0,(0,),"X"),(1,0,63)]))["counts"] == {"1":1000}
assert run(trajectory(classical=64,bits=(0,),steps=[(0,(0,),"X"),(1,0,63),(3,2**63,2**63,(1,),"X"),(1,1,0)]))["counts"] == {"1":1000}
assert run(trajectory(qubits=0,classical=0,bits=(),shots=1))["counts"] == {"":1}
assert run(trajectory(qubits=0,classical=0,bits=(),shots=0))["counts"] == {}
for cut in range(len(t)):
    run(t[:cut],success=False)
for bad in [trajectory(classical=65),trajectory(classical=0,bits=(),steps=[(1,0,0)]),
            trajectory(bits=(0,0)),trajectory(steps=[(1,2,0)]),trajectory(steps=[(1,0,2)]),
            trajectory(qubits=0,steps=[(2,0)]),trajectory(steps=[(3,4,4,(0,),"X")]),
            trajectory(steps=[(3,1,2,(0,),"X")]),trajectory(steps=[(3,1,1,(0,),"[2,0;0,1]")]),
            trajectory(steps=[(6,0)]),t+b"x"]:
    run(bad,success=False)
for expression in ["amplitude_damping(1)","amplitude_damping(1,0)","phase_amplitude_damping(1,0,0)"]:
    result = run(trajectory(qubits=1,classical=1,bits=(0,),steps=[(0,(0,),"X"),(4,(0,),expression),(1,0,0)]))
    assert result["counts"] == {"0":1000}, (expression,result)
noise = trajectory(steps=[(0,(0,),"H"),(0,(0,1),"CX"),(4,(1,),"amplitude_damping(0.5)"),(1,0,0),(1,1,1)],shots=10000)
r = run(noise)
assert set(r["counts"]) == {"00","10","11"}
assert abs(r["counts"]["00"]-5000)<300 and abs(r["counts"]["10"]-2500)<250
assert run(noise) == r
phase = run(trajectory(qubits=1,classical=1,bits=(0,),steps=[(0,(0,),"H"),(4,(0,),"phase_damping(1)"),(0,(0,),"H"),(1,0,0)],shots=10000))
assert set(phase["counts"]) == {"0","1"} and abs(phase["counts"]["0"]-5000)<300
for expression in ["H","vector([2,0;0,1])","vector([1,0;0,0])","amplitude_damping(2)","amplitude_damping(t)","vector([1,0,0;0,1,0;0,0,1])"]:
    run(trajectory(steps=[(4,(0,),expression)],shots=0),success=False)
for cut in range(len(noise)):
    run(noise[:cut],success=False)
flip = "[0,1;1,0]"
assert run(trajectory(steps=[(0,(0,),"X"),(1,0,0),(5,(0,),flip),(1,0,1)]))["counts"] == {"01":1000}
assert run(trajectory(classical=3,bits=(0,1,2),steps=[(1,0,0),(5,(0,),flip),(3,1,1,(1,),"X"),(1,1,1),(1,0,2)]))["counts"] == {"110":1000}
assert run(trajectory(qubits=0,classical=64,bits=(63,0),steps=[(5,(63,0),"[0,0,0,1;0,1,0,0;0,0,1,0;1,0,0,0]")]))["counts"] == {"11":1000}
readout = trajectory(qubits=0,classical=1,bits=(0,),steps=[(5,(0,),"[0.75,0.25;0.5,0.5]")],shots=10000)
r = run(readout)
assert set(r["counts"]) == {"0","1"} and abs(r["counts"]["1"]-2500)<250
assert run(readout) == r
assert run(trajectory(qubits=0,classical=1,bits=(0,),steps=[(5,(0,),flip)],shots=0))["counts"] == {}
for expression in ["1","[1;0]","[0.2,0.2;0,1]","[-0.1,1.1;0,1]","[i,1-i;0,1]","[a,1-a;0,1]","[infinity,0;0,1]"]:
    run(trajectory(steps=[(5,(0,),expression)],shots=0),success=False)
for targets in [(),(0,0),(2,),tuple(range(9))]:
    run(trajectory(steps=[(5,targets,flip)]),success=False)
run(trajectory(classical=0,bits=(),steps=[(5,(0,),flip)]),success=False)
for cut in range(len(readout)):
    run(readout[:cut],success=False)
print(f"PASS: {checks} numerical sampling process checks.")

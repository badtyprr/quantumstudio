"""Execute finite instances of the three-step IBM Grover algorithm panel."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm032-inventory.json").read_bytes())
assert [p["title"] for p in inventory["panels"]] == ["Grover's algorithm"]


def lines(*items):
    return "".join(f"{item}\n" for item in items).encode()


def gate(wires, matrix):
    data = matrix.encode()
    return lines(0,len(wires),*wires,len(data)) + data


def phase_oracle(size, marked):
    return "["+";".join(",".join("0" if i != j else "-1" if i in marked else "1"
                                 for j in range(size)) for i in range(size))+"]"


def measure(qubits, wires, steps):
    request = b"QEXACT1\n"+lines(qubits,qubits,qubits,*wires,len(steps))+b"".join(steps)
    p = subprocess.run([worker,"--exact-circuit"],input=request,env=env,capture_output=True,timeout=90,check=True)
    return json.loads(p.stdout)["probabilities"]


def check(qubits, marked, iterations):
    wires = list(range(qubits))
    size = 2**qubits
    hadamards = [gate([wire], "H") for wire in wires]
    if qubits == 7:
        # Use compact projectors to express the seven-wire oracle and diffuser.
        projectors = [f"2*basis({i},{size})*dagger(basis({i},{size}))" for i in marked]
        phase = gate(wires, f"identity({size})-"+"-".join(projectors))
        zero_reflection = gate(wires, f"2*basis(0,{size})*dagger(basis(0,{size}))-identity({size})")
    else:
        phase = gate(wires, phase_oracle(size, marked))
        zero_reflection = gate(wires, phase_oracle(size, range(1,size)))
    steps = hadamards + ([phase] + hadamards + [zero_reflection] + hadamards)*iterations
    steps += [lines(1,wire,wire) for wire in wires]
    probabilities = measure(qubits,wires,steps)
    # Reference evolution by sign inversion and reflection about the mean.
    amplitudes = [Fraction(1)]*size
    for _ in range(iterations):
        flipped = [-v if i in marked else v for i,v in enumerate(amplitudes)]
        mean = sum(flipped)/size
        amplitudes = [2*mean-v for v in flipped]
    for i, amplitude in enumerate(amplitudes):
        label = format(i, f"0{qubits}b")
        expected = amplitude**2/size
        actual = Fraction(probabilities.get(label,"0").replace(" Ã¢Ë†â€¢ ","/"))
        assert actual == expected, (qubits,marked,iterations,label,actual,expected)
    return dict(qubits=qubits,marked=marked,iterations=iterations,outcomes=size,
                marked_probability=str(sum(amplitudes[i]**2/size for i in marked)))


def kickback(marked):
    # Q_f acts as (x,y) -> (x,y XOR f(x)); the last wire is its target.
    wires = [0,1,2]
    matrix = "["+";".join(",".join("1" if row == (col ^ int(col//2 in marked)) else "0"
                                  for col in range(8)) for row in range(8))+"]"
    preparation = [gate([2],"X")] + [gate([wire],"H") for wire in wires]
    # The final Hadamards reveal relative signs and return the ancilla to |1>.
    steps = preparation + [gate(wires,matrix)] + [gate([wire],"H") for wire in wires]
    steps += [lines(1,wire,wire) for wire in wires]
    observed = measure(3,wires,steps)
    for j in range(4):
        amplitude = sum((-1)**(int(x in marked)+(x & j).bit_count()) for x in range(4))
        for y in range(2):
            label = format(2*j+y,"03b")
            expected = Fraction(amplitude**2,16) if y else Fraction(0)
            assert Fraction(observed.get(label,"0").replace(" ∕ ","/")) == expected
    return dict(marked=marked,outcomes=8)


cases = [check(n,marked,t) for n,marked in [(2,[3]),(3,[2]),(3,[0,7]),(3,[1,3,6])] for t in range(4)]
cases.extend(check(7,[127],t) for t in (1,3))
kickback_cases = [kickback(marked) for marked in ([], [1], [0,2], [0,1,2,3])]
print(json.dumps(dict(source=inventory["source"], source_sha256=inventory["source_sha256"],
                      worker_sha256=sha256(worker.read_bytes()).hexdigest(), cases=cases, kickback=kickback_cases),indent=2))

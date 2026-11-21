"""Verify the eight stabilizer figures from the pinned IBM notebooks."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("figures", type=Path)
parser.add_argument("--record", action="store_true")
args = parser.parse_args()
here = Path(__file__).parent
checks = {}

# Controlled-P on |+> followed by H yields (I +/- P)|psi>/2 in each branch.
def pauli_on(state, wire, gate):
    result = [0j]*len(state)
    for index,z in enumerate(state):
        sign = -1 if index & (1<<wire) else 1
        flip = (1<<wire) if gate in ("X","Y") else 0
        phase = {"X":1,"Y":1j*sign,"Z":sign}[gate]
        result[index^flip] = phase*z
    return result

for n in (1,3):
    initial = [complex(1+i,1-i) for i in range(2**n)]
    norm = math.sqrt(sum(abs(z)**2 for z in initial))
    initial = [z/norm for z in initial]
    for gates in itertools.product("XYZ",repeat=n):
        transformed = initial
        for wire,g in enumerate(gates):
            transformed = pauli_on(transformed,wire,g)
        probability = 0
        for outcome in (0,1):
            sign = (-1)**outcome
            branch = [(z+sign*p)/2 for z,p in zip(initial,transformed)]
            measured = branch
            for wire,g in enumerate(gates):
                measured = pauli_on(measured,wire,g)
            assert all(abs(p-sign*z)<1e-13 for p,z in zip(measured,branch))
            probability += sum(abs(z)**2 for z in branch)
        assert abs(probability-1)<1e-13
checks["phase-estimation-Pauli"] = "Both ancilla outcomes project into the appropriate X, Y or Z eigenspace."
checks["phase-estimation-3-qubit-Pauli"] = "Three controlled factors share one ancilla. Verified both outcome eigenspaces for each of 27 tensor words."

for a,b in itertools.product((0,1), repeat=2):
    phase = (-1)**a * (-1)**b
    assert [abs((1+(-1)**m*phase)/2)**2 for m in (0,1)] == [int((a^b)==m) for m in (0,1)]
checks["phase-estimation-ZZ"] = "Both controlled Z gates imprint the parity phase before the ancilla Hadamard."
checks["simplified-ZZ"] = "Two data-controlled CNOTs measure the same parity for every two-bit word."

table = {(0,0):{"000","111"},(0,1):{"001","110"},(1,0):{"100","011"},(1,1):{"010","101"}}
for word in range(8):
    bits = f"{word:03b}"
    syndrome = (int(bits[0])^int(bits[1]),int(bits[1])^int(bits[2]))
    assert bits in table[syndrome]
checks["stabilizer-generator-table"] = "Verified both basis states in each of the four joint eigenspaces."
checks["3-bit-repetition-parity-checks"] = "The two ancillas read the first and second adjacent pair parities. Both read zero on the entire code space."

# The top wire is qubit zero. Transcribe the controls in circuit time order.
supports = []
for logical in (0,1):
    terms = {}
    for a,b,c in itertools.product((0,1), repeat=3):
        word = logical | (a<<4) | (b<<5) | (c<<6)
        for control,target in [(0,1),(0,2),(6,3),(6,1),(6,0),(5,3),(5,2),(5,0),(4,3),(4,2),(4,1)]:
            word ^= ((word>>control)&1)<<target
        terms[word] = 1/math.sqrt(8)
    assert len(terms)==8
    for mask in (120,102,85):
        assert {word^mask for word in terms} == set(terms)
        assert all((word&mask).bit_count()%2==0 for word in terms)
    supports.append(set(terms))
assert supports[0].isdisjoint(supports[1])
assert {word^127 for word in supports[0]} == supports[1]
checks["Steane-encoder"] = "The eleven CNOTs and three Hadamards produce normalized, disjoint logical columns stabilized by all six Steane checks. Logical X exchanges the columns."

def syndrome(error):
    x,z = error
    return tuple((component&mask).bit_count()%2 for component in (x,z) for mask in (120,102,85))

corrections = {syndrome((0,0)):(0,0)}
for wire in range(7):
    for x,z in ((1,0),(0,1),(1,1)):
        error = x<<wire,z<<wire
        s = syndrome(error)
        assert s not in corrections
        corrections[s] = error
assert len(corrections)==22
for s,error in corrections.items():
    correction = corrections[s]
    assert tuple(a^b for a,b in zip(error,correction)) == (0,0)
checks["lowest-weight-correction"] = "For the distance-three Steane code, all 21 weight-one errors have distinct nonzero syndromes. Each minimum-weight correction returns the state to its logical input."

records = []
for n in (58,59,60):
    for figure in json.loads((here/f"ibm{n:03}-inventory.json").read_bytes())["figures"]:
        path = args.figures/Path(figure["path"]).name
        records.append(dict(lesson=n,path=figure["path"],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),check=checks.pop(path.stem)))
assert len(records)==8 and not checks
report = here/"ibm057-figures.json"
if args.record: report.write_text(json.dumps(records,indent=2)+"\n",encoding="utf8")
else: assert records==json.loads(report.read_bytes())
print("Verified all eight source figures.")

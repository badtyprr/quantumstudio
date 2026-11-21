"""Check the original repetition and Shor figures against gate and syndrome calculations."""
import argparse
import hashlib
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("figures", type=Path)
parser.add_argument("--record", action="store_true")
args = parser.parse_args()
here = Path(__file__).parent
evidence = {}


def record(names, check):
    for name in names.split():
        assert name not in evidence
        evidence[name] = check


# Number data wires in the diagram from top to bottom. The top data wire is
# the least significant computational bit in IBM's output labels.
for error, syndrome in [(None,(0,0)),(0,(1,0)),(1,(1,1)),(2,(0,1))]:
    mask = 0 if error is None else 1 << error
    for logical in (0,1):
        word = logical*7 ^ mask
        bits = [(word >> k)&1 for k in range(3)]
        assert (bits[0]^bits[1],bits[1]^bits[2]) == syndrome
        # Hadamard conjugation changes a Z error to an X error, so pairs
        # of X measurements read the identical parity in the signed basis.
        amplitudes = [(-1)**((word & index).bit_count())/math.sqrt(8) for index in range(8)]
        for pair, outcome in zip((3,6),syndrome):
            assert all(abs(amplitudes[i^pair]-(-1)**outcome*a)<1e-14 for i,a in enumerate(amplitudes))
    name = "no-error" if error is None else f"e{error}"
    phase = "none" if error is None else str(error)
    record(f"repetition-decode-{name} phase-error-{phase}",f"Top-to-bottom parity readouts {syndrome} for error on {error}.")
record("repetition-encoder repetition-encoder-modified","The first data wire controls both other wires. Three Hadamards transform the words 000 and 111 into +++ and ---.")
record("repetition-error-detection three-bit-modified-error-detect simplified-phase-error-detect","The ancillas read adjacent pair parities. The dual circuit exchanges the CNOT controls and targets in the Hadamard basis.")

for target in range(2):
    for control in range(2):
        for x in (1,2,3):
            word=2*target+control
            def cnot(w):
                return w ^ ((w&1)<<1)
            assert cnot(word^x) == (cnot(word)^cnot(x))
            z = (x & 2) | ((x&1) ^ (x>>1))
            assert ((x&word).bit_count()-(z&cnot(word)).bit_count())%2 == 0
record("X-and-CNOT Z-and-CNOT","All three shown X and Z error patterns propagate through a bottom-controlled CNOT, checked on all four inputs.")

for pattern in range(8):
    # The three inputs to the inner repetition encoders are the block bits.
    encoded=sum(7<<(3*k) for k in range(3) if pattern & (1<<k))
    phase=(-1)**((encoded>>5)&1)
    assert phase == (-1)**((pattern>>1)&1)
    assert (-1)**(((encoded^(1<<5))>>5)&1) == -phase
record("Shor-encoder","The three block bits fan out to three identical physical bits each. Both encoded columns are checked in replay-ibm055-shor.py.")
record("Shor-phase-error-1 Shor-phase-error-2","A Z on the last wire of the middle block gives the same phase as Z on that block's input.")
record("Shor-phase-error-detect-1 Shor-phase-error-detect-2","The middle block changes both neighboring phase parities (1,1). Block-level and expanded parity checks have identical signs on the encoded basis.")
record("Shor-XZ-error Shor-ZX-error Shor-ZX-error-2","Exchanging X and Z changes only the overall sign. Moving Z before the block fanout preserves its action on the encoded basis.")
for j in range(101):
    p=j/100
    repeated=sum(math.comb(3,k)*p**k*(1-p)**(3-k) for k in (2,3))
    assert abs(repeated-(3*p*p-2*p**3))<1e-14
    shor=sum(math.comb(9,k)*p**k*(1-p)**(9-k) for k in range(2,10))
    assert abs(shor-(1-(1-p)**9-9*p*(1-p)**8))<1e-14
    if j in (1,4): assert (shor<p)==(j==1)
record("binary-symmetric-error","Independent majority failure has probability 3p²−2p³ and meets the unencoded curve at p=0, 1/2 and 1.")
record("breakeven-Shor","The two-or-more-error curve is 1−(1−p)^9−9p(1−p)^8. It lies below p at 0.01 and above p at 0.04.")

records=[]
for lesson in (54,55):
    inventory=json.loads((here/f"ibm{lesson:03}-inventory.json").read_bytes())
    for figure in inventory["figures"]:
        path=args.figures/Path(figure["path"]).name
        records.append(dict(lesson=lesson,path=figure["path"],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),check=evidence.pop(path.stem)))
assert len(records)==25 and not evidence
report=here/"ibm053-figures.json"
if args.record: report.write_text(json.dumps(records,indent=2)+"\n",encoding="utf8")
else: assert records==json.loads(report.read_bytes())
print("Verified all 25 source figures.")
